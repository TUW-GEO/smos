"""
Module to synchronize SMOS L3 SM data from the CATDS FTP server to local disk.

SMOS L3 Ascending and Descending products (A: ascending=6am and
D: descending=6pm) of all processing campaigns: the operational one (OPER)
and reprocessings (RE07, ...).

Downloaded from CATDS (https://www.catds.fr/Products/Available-products-from-CPDC)::

    ftp ftp.ifremer.fr
    user : ext-catds-cpdc
    password : catds2010

On the server, files are organised as::

    /Land_products/GRIDDED/L3SM/<campaign>/MIR_<product><A|D>/<YYYY>/<DOY|MM>/*.tgz

where <campaign> is OPER or a reprocessing (RE<nn>, currently RE07). The
campaigns are not hard-coded but read from the server, so that a new
reprocessing (e.g. RE08) is downloaded the same way as RE07.
Daily products (CLF31, CLF3S) are stored in day-of-year folders, all other
products in monthly folders. Each .tgz archive contains a .DBL.nc and .HDR file.

Locally, data from all campaigns (e.g. RE07 and OPER) is mixed in the same
folders (the reader uses the file with the highest version for each date)::

    <local_root>/MIR_<product><A|D>/<YYYY>/<DOY|MM>/*.(tgz|DBL.nc|HDR)

The archives are kept (so that they are not downloaded again) and extracted
next to them.
"""
import os
import re
import tarfile
import warnings
from pathlib import Path, PurePosixPath
import subprocess
from datetime import datetime
from calendar import monthrange
import pandas as pd
import yaml

from smos.misc import get_first_last_day_images, _get_date

L3_START_DATE = datetime(2010, 1, 17)
L3_ORBITS = ('ASC', 'DES')
# Processing campaign folders on the server: OPER and reprocessings RE<nn>
L3_CAMPAIGN_PATTERN = re.compile(r'^(OPER|RE\d+)$')

# Product: (folder type on server, temporal resolution of the images)
L3_PRODUCTS = {
    'CLF3S': ('doy', 'daily'),     # Daily SM (UDP product)
    'CLF31': ('doy', 'daily'),     # Daily retrieval (full set of variables)
    'CLF33': ('month', 'daily'),   # 3-day aggregate (one file per start day)
    'CLF3E': ('month', 'daily'),   # 3-day aggregate dielectric constant
    'CLF3D': ('month', 'dekad'),   # 10-day aggregate (median, min, max)
    'CLF3M': ('month', 'monthly'),  # Monthly aggregate
}


def product_folder(product, orbit):
    """
    Name of the folder for a product and orbit, as on the server,
    e.g. MIR_CLF3SA for product CLF3S and orbit ASC.
    """
    product = product.upper().replace('MIR_', '')
    if product not in L3_PRODUCTS:
        raise ValueError(f"Unknown product {product}, choose from "
                         f"{list(L3_PRODUCTS.keys())}")
    orbit = orbit.upper()
    if orbit not in L3_ORBITS:
        raise ValueError(f"Unknown orbit {orbit}, choose from {L3_ORBITS}")
    return f"MIR_{product}{orbit[0]}"


def campaign_sort_key(campaign):
    """
    Sort key for processing campaigns: reprocessings by their number, the
    operational campaign (OPER, the most recent data) last.
    """
    if campaign == 'OPER':
        return (1, 0)
    return (0, int(campaign[2:]))


def local_campaigns(path):
    """
    Processing campaigns of the files (.tgz or .DBL.nc) found under the
    passed (local) path, from the file names (SM_<campaign>_MIR_...).

    Returns
    -------
    campaigns: list
        Sorted campaign names (OPER last).
    """
    campaigns = set()
    for _, _, files in os.walk(path):
        for f in files:
            m = re.match(r'^SM_([A-Z0-9]+)_MIR_.*\.(tgz|DBL\.nc)$', f)
            if m and L3_CAMPAIGN_PATTERN.match(m.group(1)):
                campaigns.add(m.group(1))
    return sorted(campaigns, key=campaign_sort_key)


def extract_archives(path, overwrite=False):
    """
    Extract all .tgz archives (recursively) under the passed path into the
    folder where the archive is stored. Archives are only extracted if the
    contained .DBL.nc file does not exist yet. Damaged or incomplete archives
    (e.g. after an interrupted download, they are completed by the next
    download) are skipped with a warning. Files are only created once an
    archive was extracted completely.

    Parameters
    ----------
    path: str
        Root path to search for archives
    overwrite: bool, optional (default: False)
        Extract archives again even if the netcdf file already exists.

    Returns
    -------
    extracted: list
        Paths of all extracted files.
    """
    extracted = []
    for root, _, files in os.walk(path):
        for f in sorted(files):
            if not f.endswith('.tgz'):
                continue
            nc = os.path.join(root, f.replace('.tgz', '.DBL.nc'))
            if os.path.isfile(nc) and not overwrite:
                continue
            parts = {}  # temporary file -> final file
            try:
                with tarfile.open(os.path.join(root, f), 'r:gz') as tar:
                    for member in tar.getmembers():
                        # only plain files without any directory component
                        name = os.path.basename(member.name)
                        if not member.isfile() or name != member.name:
                            raise ValueError(f"Unexpected member "
                                             f"{member.name} in archive {f}")
                        target = os.path.join(root, name)
                        with tar.extractfile(member) as src, \
                                open(target + '.part', 'wb') as dst:
                            dst.write(src.read())
                        parts[target + '.part'] = target
            except (tarfile.TarError, EOFError, OSError) as e:
                for part in parts:
                    os.remove(part)
                warnings.warn(f"Could not extract {os.path.join(root, f)} "
                              f"(damaged or incomplete archive): {e}")
                continue
            except ValueError:
                for part in parts:
                    os.remove(part)
                raise
            for part, target in parts.items():
                os.replace(part, target)
                extracted.append(target)
    return extracted


class SmosL3Ftp:
    def __init__(self, local_root, product='CLF3S', orbits=L3_ORBITS,
                 campaigns=None, username='ext-catds-cpdc',
                 password='catds2010', skip_lftp_verify=False):
        """
        Access to SMOS L3 SM data on the CATDS FTP server.

        Parameters
        ----------
        local_root: str
            Local root folder where the data from the FTP server is transferred
            into. A subfolder for each product and orbit is created there, e.g.
            MIR_CLF3SA.
        product: str, optional (default: 'CLF3S')
            Which L3 product to download, one of
            - CLF3S: Daily soil moisture (UDP product)
            - CLF31: Daily retrieval (all variables)
            - CLF33: 3-day aggregate
            - CLF3E: 3-day aggregate dielectric constant (no soil moisture)
            - CLF3D: 10-day aggregate (median, min, max)
            - CLF3M: Monthly aggregate
        orbits: tuple or str, optional (default: ('ASC', 'DES'))
            Which overpasses to download, ASC (6am) and/or DES (6pm).
        campaigns: tuple or str, optional (default: None)
            Which processing campaigns to download, e.g. RE07 (reprocessed
            record, 2010-2021) and/or OPER (operational, since 2021). All are
            stored in the same local folder. By default, all campaigns that
            are available on the server are used (see `available_campaigns`).
        username: str, optional (default: 'ext-catds-cpdc')
            Username for the CATDS FTP server (public CATDS account)
        password: str, optional (default: 'catds2010')
            Password for the CATDS FTP server (public CATDS account)
        skip_lftp_verify: bool, optional (default: False)
            Skip checking if lftp is available (for testing).
        """
        self.host = "ftp://ftp.ifremer.fr"
        self.ftp_root = PurePosixPath("/", "Land_products", "GRIDDED", "L3SM")

        self.product = product.upper().replace('MIR_', '')
        if isinstance(orbits, str):
            orbits = [orbits]
        self.folders = [product_folder(self.product, o) for o in orbits]
        if campaigns is not None:
            if isinstance(campaigns, str):
                campaigns = [campaigns]
            campaigns = [c.upper() for c in campaigns]
            for c in campaigns:
                if not L3_CAMPAIGN_PATTERN.match(c):
                    raise ValueError(f"Invalid campaign {c}, expected OPER "
                                     f"or RE<nn> (e.g. RE07)")
            campaigns = sorted(campaigns, key=campaign_sort_key)
        self._campaigns = campaigns
        self.folder_type, self.temp_res = L3_PRODUCTS[self.product]

        self.username = username
        self.password = password

        self.local_root = Path(local_root)
        os.makedirs(self.local_root, exist_ok=True)

        if not skip_lftp_verify:
            self.verify_lftp_installed()

    @property
    def campaigns(self):
        """
        Selected processing campaigns (sorted, OPER last). If none were
        passed, all campaigns available on the server are used.
        """
        if self._campaigns is None:
            self._campaigns = self.available_campaigns()
        return self._campaigns

    @campaigns.setter
    def campaigns(self, campaigns):
        self._campaigns = campaigns

    def available_campaigns(self):
        """
        Processing campaigns (OPER and reprocessings RE<nn>) on the server.

        Returns
        -------
        campaigns: list
            Campaign names, sorted by their number, OPER last.
        """
        return sorted([d for d in self.list(filter='dir')
                       if L3_CAMPAIGN_PATTERN.match(d)],
                      key=campaign_sort_key)

    def verify_lftp_installed(self):
        """
        Call lftp command to check if program is available.
        Otherwise it has to be installed e.g. via apt-get install.
        """
        try:
            r = subprocess.run(["lftp", "--version"], capture_output=True)
        except FileNotFoundError:
            r = None

        if r is None or r.returncode != 0:
            raise ValueError("lftp command is not available. "
                             "Please install lftp: https://lftp.yar.ru/")

    def exec(self, cmd):
        cmd = [
            "lftp", "-c",
            f"set ftp:ssl-allow no && set net:max-retries 3 && "
            f"open -u {self.username},{self.password} {self.host} && "
            f"{cmd} && "
            f"quit"
        ]

        r = subprocess.run(cmd, capture_output=True)

        return r

    def list(self, subpath='', filter='all'):
        """
        Create a list of all files and subdirectories under the passed
        path on the server.

        Parameters
        ----------
        subpath: str, optional (default: '')
            Subdirectory on the server to look into, relative to the L3SM
            root, e.g. 'OPER/MIR_CLF3SA/2022/001'
        filter: str, optional (default: 'all')
            - all: returns files and folders
            - file: returns only files
            - dir: returns only directories

        Returns
        -------
        elements: list
            Sorted list of all files and/or folders under the subpath. Folder
            names don't have a trailing slash. index.html files are ignored.
        """
        path = self.ftp_root
        if subpath not in [None, '']:
            path = path / PurePosixPath(subpath)
        r = self.exec(f"cls -1 {path}/")
        lst = r.stdout.decode("utf-8").splitlines()

        data = []
        for line in lst:
            is_dir = line.endswith('/')
            d = line.rstrip('/').split('/')[-1]
            if d == 'index.html' or d == '':
                continue
            if is_dir and (filter in ['dir', 'all']):
                data.append(d)
            if not is_dir and (filter in ['file', 'all']):
                data.append(d)

        return sorted(data)

    def last_available_day(self):
        """
        Get the start date of the latest available file on the server
        (over all selected campaigns).
        If multiple orbits are selected, the earliest of the last days of
        all orbits is returned (i.e. the last day available for all orbits).

        Returns
        -------
        last_date: datetime
            Last day for which data is available on the server.
        """
        last_days = []
        for folder in self.folders:
            folder_last_days = [d for d in (self._last_day(c, folder)
                                            for c in self.campaigns)
                                if d is not None]
            if len(folder_last_days) == 0:
                raise ValueError(f"No {folder} data found on the server for "
                                 f"campaigns {self.campaigns}")
            last_days.append(max(folder_last_days))

        last_day = min(last_days)

        return datetime(last_day.year, last_day.month, last_day.day)

    def _last_day(self, campaign, folder):
        # Start date of the last file of a campaign and folder on the server,
        # None if there is no file.
        base = f"{campaign}/{folder}"
        for year in reversed(self.list(base, filter='dir')):
            for sub in reversed(self.list(f"{base}/{year}", filter='dir')):
                files = [f for f in self.list(f"{base}/{year}/{sub}",
                                              filter='file')
                         if f.endswith('.tgz')]
                if len(files) > 0:
                    return _get_date(files[-1])
        return None

    def _mirror_cmd(self, campaign, folder, subpath, globs=None, opts=''):
        # Create the lftp mirror command for one (campaign) folder on the
        # server. Files are (optionally) selected via the passed date globs.
        target_path = self.local_root / folder / subpath

        cmd = ["mirror -c"]
        if len(opts) > 0:
            cmd.append(opts)
        if globs is None:
            cmd.append("--include-glob '*.tgz'")
        else:
            for g in globs:
                cmd.append(f"--include-glob '*_{g}T000000_*.tgz'")
        cmd.append(str(self.ftp_root / campaign / folder /
                       PurePosixPath(subpath)))
        cmd.append(f"{target_path}")
        cmd.append('--no-perms')

        return ' '.join(cmd)

    def _year_cmds(self, campaign, folder, year, days, opts=''):
        # Create the mirror commands for one campaign, folder and year
        # to download all files with a start date in `days`.
        # Only existing subfolders on the server are synchronised.
        n_days = pd.Timestamp(year, 12, 31).dayofyear
        if len(days) == n_days:
            return [self._mirror_cmd(campaign, folder, str(year), opts=opts)]

        available = self.list(f"{campaign}/{folder}/{year}", filter='dir')
        cmds = []
        if self.folder_type == 'doy':
            for d in days:
                sub = f"{d.dayofyear:03}"
                if sub in available:
                    cmds.append(self._mirror_cmd(
                        campaign, folder, f"{year}/{sub}", opts=opts))
        else:
            for month in sorted(set(days.month)):
                ms = days[days.month == month]
                sub = f"{int(month):02}"
                if sub not in available:
                    continue
                if len(ms) == monthrange(year, int(month))[1]:
                    globs = None  # complete month
                else:
                    globs = [f"{d.year}{d.month:02}{d.day:02}" for d in ms]
                cmds.append(self._mirror_cmd(
                    campaign, folder, f"{year}/{sub}", globs, opts=opts))
        return cmds

    def sync_period(self, startdate, enddate, opts='', dry_run=False,
                    extract=True):
        """
        Synchronize SMOS L3 data between local root and FTP folder for files
        with a start date in the passed time frame (for all selected orbits
        and campaigns). All files of a complete year are downloaded in one
        command, otherwise only the required day/month folders are mirrored.

        Parameters
        ----------
        startdate: str or datetime
            First day to download data for (if available)
        enddate: str or datetime
            Last day to download data for (if available)
        opts: str, optional, default: ''
            Additional options that are added to the lftp mirror command.
            For all options see https://lftp.yar.ru/lftp-man.html
        dry_run: bool, optional, default=False
            Dry run does not actually download anything. Instead, the
            commands are returned.
        extract: bool, optional (default: True)
            Extract the downloaded .tgz archives.

        Returns:
        -------
        ret: list
            List of return values or commands (if dry_run was chosen).
        """
        startdate = max(pd.to_datetime(startdate), pd.Timestamp(L3_START_DATE))
        enddate = pd.to_datetime(enddate)
        days = pd.date_range(startdate, enddate, freq='D')

        ret = []
        for campaign in self.campaigns:
            for folder in self.folders:
                years = self.list(f"{campaign}/{folder}", filter='dir')
                for year in sorted(set(days.year)):
                    if str(year) not in years:
                        continue
                    cmds = self._year_cmds(campaign, folder, int(year),
                                           days[days.year == year], opts=opts)
                    if len(cmds) == 0:
                        continue
                    if dry_run:
                        ret += cmds
                    else:
                        ret.append(self.exec(' && '.join(cmds)))

        if not dry_run:
            if extract:
                for folder in self.folders:
                    extract_archives(self.local_root / folder)
            self.write_overview()

        return ret

    def write_overview(self):
        """
        Write the overview.yml file in each product folder in the local
        root, containing the first and last day of locally available data
        and the processing campaigns of the local files.
        """
        for folder in self.folders:
            path = self.local_root / folder
            first_day, last_day = None, None
            if os.path.isdir(path):
                first_day, last_day = get_first_last_day_images(str(path))

            props = dict(
                comment="DO NOT CHANGE THIS FILE MANUALLY! Required for data update.",
                first_day=str(first_day) if first_day is not None else None,
                last_day=str(last_day) if last_day is not None else None,
                campaigns=local_campaigns(path),
                last_update=str(datetime.now()))

            os.makedirs(path, exist_ok=True)
            with open(os.path.join(path, 'overview.yml'), 'w') as f:
                yaml.dump(props, f, default_flow_style=False, sort_keys=False)
