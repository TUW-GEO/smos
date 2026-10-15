"""
Module to synchronize SMOS IC data from the CATDS HTTPS server to local disk.

Data is available at
https://data.catds.fr/cecsm/Land_products/L3_SMOS_IC_Soil_Moisture/
No authentication is required. SMOS IC is a scientific (i.e. not operational)
product, so the record on the server is not updated regularly.

On the server (and locally) files are organised as
    <ASC|DES>/<YYYY>/SM_*_MIR_CDF3S<A|D>_<YYYYMMDD>T000000_*.DBL.nc
"""
import os
from pathlib import Path, PurePosixPath
import subprocess
from datetime import datetime
from calendar import monthrange
import pandas as pd
from tqdm import tqdm
import yaml

from smos.misc import get_first_last_day_images, _get_date

IC_START_DATE = datetime(2010, 1, 12)
IC_ORBITS = ('ASC', 'DES')


class SmosIcHttp:
    def __init__(self, local_root, orbits=IC_ORBITS, skip_lftp_verify=False):
        """
        Access to SMOS IC data on the CATDS HTTPS server.

        Parameters
        ----------
        local_root: str
            Local root folder where the data from the server is transferred
            into. Subfolders for each orbit (ASC, DES) are created.
        orbits: tuple or str, optional (default: ('ASC', 'DES'))
            Which overpasses to download, ASC (6am) and/or DES (6pm).
        skip_lftp_verify: bool, optional (default: False)
            Skip checking if lftp is available (for testing).
        """
        self.host = "https://data.catds.fr"
        self.remote_root = PurePosixPath(
            "/", "cecsm", "Land_products", "L3_SMOS_IC_Soil_Moisture")

        if isinstance(orbits, str):
            orbits = [orbits]
        orbits = [str(o).upper() for o in orbits]
        for o in orbits:
            if o not in IC_ORBITS:
                raise ValueError(f"Unknown orbit {o}, choose from {IC_ORBITS}")
        self.orbits = orbits

        self.local_root = Path(local_root)
        os.makedirs(self.local_root, exist_ok=True)

        if not skip_lftp_verify:
            self.verify_lftp_installed()

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
            f"open {self.host} && "
            f"{cmd} && "
            f"quit"
        ]

        r = subprocess.run(cmd, capture_output=True)

        return r

    def list(self, subpath='', filter='all'):
        """
        Create a list of all files and subdirectories under the passed
        path on the server. The HTTP listing does not distinguish between
        files and folders, therefore folders are identified by their
        name (orbit or year).

        Parameters
        ----------
        subpath: str, optional (default: '')
            Subdirectory on the server to look into, e.g. 'ASC/2018'
        filter: str, optional (default: 'all')
            - all: returns files and folders
            - file: returns only files (ending with .nc)
            - dir: returns only directories (orbits or years)

        Returns
        -------
        elements: list
            Sorted list of all files and/or folders under the subpath
        """
        path = self.remote_root
        if subpath not in [None, '']:
            path = path / PurePosixPath(subpath)
        r = self.exec(f"cls {path}/")
        lst = r.stdout.decode("utf-8").splitlines()

        data = []
        for l in lst:
            d = l.rstrip('/').split('/')[-1]
            is_dir = d.isdigit() or (d in IC_ORBITS)
            is_file = d.endswith('.nc')
            if is_dir and (filter in ['dir', 'all']):
                data.append(d)
            if is_file and (filter in ['file', 'all']):
                data.append(d)

        return sorted(data)

    def last_available_day(self):
        """
        Get the latest available day on the server (from the file names).
        If multiple orbits are selected, the earliest of the last days of
        all orbits is returned (i.e. the last day available for all orbits).

        Returns
        -------
        last_date: datetime
            Last day for which data is available on the server.
        """
        last_days = []
        for orbit in self.orbits:
            last_year = [int(y) for y in self.list(orbit, filter='dir')][-1]
            files = self.list(f"{orbit}/{last_year}", filter='file')
            last_days.append(_get_date(files[-1]))

        last_day = min(last_days)

        return datetime(last_day.year, last_day.month, last_day.day)

    def list_all_available_days(self, date_from=IC_START_DATE,
                                date_to=None, progressbar=True):
        """
        Shortcut to get a list of all available days (i.e. files) on the
        server within the selected time frame. A day is considered available
        if a file exists for at least one of the selected orbits.

        Parameters
        ----------
        date_from: str or datetime, optional
            First date of the time frame to check available days for on server.
            By default, we use the first date of SMOS IC (2010-01-12)
        date_to: str or datetime, optional (default: None)
            Last date of the time frame to check available days for on server.
            By default (None), we use the current date.
        progressbar: bool, optional (default: True)
            This operation will send some request to the server and may take
            some time. (De)activate a visual progress representation.

        Returns
        -------
        dates: list
            Sorted list of dates for which a file exists on the server
        """
        if date_to is None:
            date_to = datetime.now()
        date_to = pd.to_datetime(date_to).to_pydatetime()
        date_from = pd.to_datetime(date_from).to_pydatetime()

        dates = set()
        for orbit in self.orbits:
            years = [int(y) for y in self.list(orbit, filter='dir')]
            years = [y for y in years
                     if (y >= date_from.year) and (y <= date_to.year)]

            for year in tqdm(years, disable=not progressbar,
                             desc=f"Scanning server folder {orbit}"):
                for f in self.list(f"{orbit}/{year}", filter='file'):
                    d = _get_date(f)
                    if d is None:
                        continue
                    dt = datetime(d.year, d.month, d.day)
                    if date_from <= dt <= date_to:
                        dates.add(dt)

        return sorted(dates)

    def _mirror_cmd(self, orbit, year, globs=None, opts=''):
        # Create the lftp mirror command for one orbit and year. Files are
        # (optionally) selected via the passed date globs.
        target_path = self.local_root / orbit / str(year)

        cmd = ["mirror -c"]
        if len(opts) > 0:
            cmd.append(opts)
        for g in (globs or []):
            cmd.append(f"--include-glob '*_{g}T000000_*'")
        cmd.append(str(self.remote_root / orbit / str(year)))
        cmd.append(f"{target_path}")
        cmd.append('--no-perms')

        return ' '.join(cmd)

    def _sync_globs(self, year, globs, opts='', dry_run=False):
        ret = []
        for orbit in self.orbits:
            cmd = self._mirror_cmd(orbit, year, globs, opts=opts)
            if dry_run:
                ret.append(cmd)
            else:
                ret.append(self.exec(cmd))
        return ret

    def sync(self, year, month=None, day=None, opts='', dry_run=False):
        """
        Download data from remote to local folder for a certain year, month
        or day for all selected orbits.

        Parameters
        ----------
        year: int
            Year part of the date to download
        month: int, optional (default: None)
            Month part of the date to download. If not set, then the whole
            year is synced.
        day: int, optional (default: None)
            Day part of the date to download. If not set, then
            the whole month is synced.
        opts: str, optional, default: ''
            Additional options that are added to the command
            mirror OPTS root_dir target_dir
            For all options see https://lftp.yar.ru/lftp-man.html
        dry_run: bool, optional, default=False
            Dry run does not actually download anything.
            Instead of the return values, the full commands are returned

        Returns
        -------
        ret: list
            Return value or command (if dry_run) for each orbit
        """
        if day is not None and month is None:
            raise ValueError("A month must be given when a day is passed.")

        if month is None:
            _d = datetime(year, 12, 31)
        else:
            _d = datetime(year, month,
                          day if day is not None else
                          monthrange(year, month)[1])
        if _d < IC_START_DATE:
            raise ValueError(f"Chosen date must be after {IC_START_DATE}")

        if month is None:
            globs = None
        elif day is None:
            globs = [f"{year}{month:02}??"]
        else:
            globs = [f"{year}{month:02}{day:02}"]

        return self._sync_globs(year, globs, opts=opts, dry_run=dry_run)

    def sync_period(self, startdate, enddate, opts='', dry_run=False):
        """
        Synchronize SMOS IC data between local root and server for days
        in the passed time frame. One command per year and orbit is sent,
        complete years and months are selected as a whole.

        Parameters
        ----------
        startdate: str or datetime
            First day to download data for (if available)
        enddate: str or datetime
            Last day to download data for (if available)
        opts: str, optional, default: ''
            Additional options that are added to the lftp mirror command.
        dry_run: bool, optional, default=False
            Dry run does not actually download anything.

        Returns:
        -------
        ret: list
            List of return values or commands (if dry_run was chosen)
        """
        startdate = max(pd.to_datetime(startdate), pd.Timestamp(IC_START_DATE))
        enddate = pd.to_datetime(enddate)

        df = pd.Series(index=pd.date_range(startdate, enddate, freq='D'),
                       data=1)

        ret = []

        for year, ys in df.groupby(df.index.year):
            year = int(year)
            if len(ys) == pd.Timestamp(year, 12, 31).dayofyear:
                globs = None  # complete year (fast)
            else:
                globs = []
                for month, ms in ys.groupby(ys.index.month):
                    month = int(month)
                    if len(ms) == monthrange(year, month)[1]:  # complete month
                        globs.append(f"{year}{month:02}??")
                    else:  # individual days
                        globs += [f"{dt.year}{dt.month:02}{dt.day:02}"
                                  for dt in ms.index]

            ret += self._sync_globs(year, globs, opts=opts, dry_run=dry_run)

        self.write_overview()

        return ret

    def write_overview(self):
        """
        Write the overview.yml file in the local root, containing the first
        and last day of locally available data. If multiple orbits are
        selected, the earliest first and last day of all orbits are used,
        so that an update starts from the last day available for all orbits.
        """
        firsts, lasts = [], []
        for orbit in self.orbits:
            path = self.local_root / orbit
            if os.path.isdir(path):
                first_day, last_day = get_first_last_day_images(str(path))
                if first_day is not None:
                    firsts.append(first_day)
                if last_day is not None:
                    lasts.append(last_day)

        props = dict(comment="DO NOT CHANGE THIS FILE MANUALLY! Required for data update.",
                     first_day=str(min(firsts)) if len(firsts) > 0 else None,
                     last_day=str(min(lasts)) if len(lasts) > 0 else None,
                     last_update=str(datetime.now()))

        with open(os.path.join(self.local_root, 'overview.yml'), 'w') as f:
            yaml.dump(props, f, default_flow_style=False, sort_keys=False)
