"""
Module to synchronize SMOS L2 data from FTP to local disk
"""
import os
from pathlib import Path
import subprocess
from datetime import datetime
from tqdm import tqdm
import pandas as pd
from calendar import monthrange
from pathlib import PurePosixPath
from smos.misc import get_first_last_day_images
import yaml

L2_START_DATE = datetime(2010, 6, 1)

def load_dotrc(path=None) -> dict:
    """
    Read FTP login credentials from .smosrc file.

    Parameters
    ----------
    path: str, optional (default: None)
        Path to the dotrc file. None will look in the default branch
        with is the home folder.

    Returns
    -------
    config: dict
        Elements from the dotrc file
    """
    if path is None:
        path = os.path.join(str(Path.home()), '.smosapirc')
    if not os.path.exists(path):
        raise ValueError(f'.smosapirc file not found at {path}. '
                         f'Create an account at https://eoiam-idp.eo.esa.int')
    config = {}
    with open(path) as f:
        for line in f.readlines():
            if "=" in line:
                k, v = line.strip().split("=", 1)
                if k in ("DISSEO_USERNAME", "DISSEO_PASSWORD"):
                    config[k] = v.strip(f""" "'""""")
    return config


class SmosDissEoFtp:
    def __init__(self, local_root, username=None, password=None, dotrc=None,
                 skip_lftp_verify=False):
        """
        Access to SMOS L2 data from FTP.

        Parameters
        ----------
        local_root: str
            Local root folder where the data from the FTP server is transferred
            into.
        username: str, optional (default: None)
            Username of your EO Sign In account. If None is passed here
            it will be derived from the .smosapirc file in the home directory.
            Create an account at https://eoiam-idp.eo.esa.int
        password: str, optional (default: None)
            Password for the EO Sign in account. If None is passed here
            it will be derived from the .smosapirc file in the home directory.
            Create an account at https://eoiam-idp.eo.esa.int
        dotrc: str, optional (default: None)
            Path to the .smosapirc file containing the FTP username and password.
            If None, then the file is assumed to be at $HOME/.smosapirc
                DISSEO_USERNAME=xxxx
                DISSEO_PASSWORD=xxxx
            Create an account at https://eoiam-idp.eo.esa.int
        skip_lftp_verify: bool, optional (default: False)
            Skip checking if lftp is available (for testing).
        """
        self.host = "ftps://smos-diss.eo.esa.int"
        self.ftp_root = PurePosixPath("/", "SMOS", "L2SM", "MIR_SMUDP2_nc")

        self.username = username
        self.password = password

        self.local_root = Path(local_root)
        os.makedirs(self.local_root, exist_ok=True)

        if self.username is None or self.password is None:
            config = load_dotrc(dotrc)
            if self.username is None:
                self.username = config['DISSEO_USERNAME']
            if self.password is None:
                self.password = config['DISSEO_PASSWORD']

        if not skip_lftp_verify:
            self.verify_lftp_installed()

    def verify_lftp_installed(self):
        """
        Call lftp command to check if program is available.
        Otherwise it has to be installed e.g. via apt-get install.
        """
        r = subprocess.run(["lftp", "--version"])

        if r.returncode != 0:
            raise ValueError("lftp command is not available. "
                             "Please install lftp: https://lftp.yar.ru/")

    def exec(self, cmd):
        cmd = [
            "lftp", "-c",
            f"open {self.host} && set ssl:verify-certificate no && "
            f"user {self.username} {self.password} && "
            f"{cmd} && "
            f"quit"
        ]

        r = subprocess.run(cmd, capture_output=True)

        return r

    def list(self, subpath='', filter='all'):
        """
        Create a list of all files and subdirectories under the passed
        path on the server.
        Directories end with /, files should have a file extension.

        Parameters
        ----------
        subpath: str, optional (default: '')
            Subdirectory on the server to look into.
            e.g. '/2020/01/01'
        filter: str, optional (default: 'all')
            - all: returns fils and folders
            - file: returns only files
            - dir: returns only directories

        Returns
        -------
        elements: list
            List of all files and/or folders under the subpath on the server
        """
        path = self.ftp_root
        if subpath not in [None, '']:
            path = path / PurePosixPath(subpath)
        cmd = f"cls {path}"
        r = self.exec(cmd)
        lst = r.stdout.decode("utf-8").splitlines()

        data = []
        for l in lst:
            d = l.split('/')[-1]
            if d == '':
                d = l.split('/')[-2]+'/'
            if d.endswith('/') and (filter in ['dir', 'all']):
                data.append(d)
            if not d.endswith('/') and (filter in ['file', 'all']):
                data.append(d)

        return data

    def last_available_day(self):
        """
        Get the latest available day on the server (incomplete directory).
        We want to exclude this day from downloading.

        Returns
        -------
        last_date:

        """
        last_year = [int(y.replace('/', '')) for y in self.list(filter='dir')][-1]
        last_month = [int(m.replace('/', '')) for m in self.list(subpath=str(last_year), filter='dir')][-1]
        last_day = [int(d.replace('/', '')) for d in self.list(subpath=f"{last_year}/{last_month:02}", filter='dir')][-1]

        return datetime(last_year, last_month, last_day)

    def list_all_available_days(self, date_from=L2_START_DATE,
                                date_to=datetime.now(), progressbar=True):
        """
        Shortcut to get a list of all available days (i.e. folders) on the
        server within the selected time frame.

        Parameters
        ----------
        date_from: str or datetime, optional
            First date of the time frame to check available days for on server.
            By default, we use the first date of SMOS L2 (2010-06-01)
        date_to: str or datetime, optional
            Last date of the time frame to check available days for on server.
            By default, we use the current date.
        progressbar: bool, optional (default: True)
            This operation will send some request to the server and may take
            some time. (De)activate a visual progress representation.

        Returns
        -------
        dates: list
            List of dates for which a folder exists on the server
        """
        date_to = pd.to_datetime(date_to).to_pydatetime()
        date_from = pd.to_datetime(date_from).to_pydatetime()

        dates = []
        years = [int(y.replace('/', '')) for y in self.list(filter='dir')]
        years = [y for y in years if ((y >= date_from.year) and (y <= date_to.year))]

        for year in tqdm(years, disable=not progressbar, description="Scanning FTP folder"):
            months = [int(m.replace('/', '')) for m in self.list(subpath=str(year), filter='dir')]
            if year == date_from.year:
                months = [m for m in months if m >= date_from.month]
            if year == date_to.year:
                months = [m for m in months if m <= date_to.month]
            for month in months:
                days = self.list(subpath=f"{year}/{month:02}", filter='dir')
                for day in days:
                    dt = datetime(int(year),
                                  int(month),
                                  int(day.replace('/', '')))
                    if date_from <= dt <= date_to:
                        dates.append(dt)

        return dates

    def sync(self, year, month, day=None, opts='', dry_run=False):
        """
        Download data from remote to local folder for a certain day.

        Parameters
        ----------
        year: int
            Year part of the date to download
        month: int
            Month part of the date to download
        day: int, optional
            Day part of the date to download. If not set, then
            the whole month is synced.
        opts: str, optional, default: ''
            Additional options that are added to the command
            mirror OPTS root_dir target_dir
            For all options see https://lftp.yar.ru/lftp-man.html
        dry_run: bool, optional, default=False
            Dry run does not actually download anything.
            Instead of the return value, the full command is returned

        Returns
        -------
        ret: str
            Return value or command (if dry_run)
        """
        _d = datetime(year, month, day if day is not None else monthrange(year, month)[1])
        if _d < L2_START_DATE:
            raise ValueError(f"Chosen date must be after {L2_START_DATE}")

        subpath = Path(str(year), f"{month:02}")

        if day is not None:
            subpath = subpath / f"{day:02}"

        target_path = self.local_root / subpath

        cmd = ["mirror -c"]
        if len(opts) > 0:
            cmd.append(opts)
        cmd.append(str(self.ftp_root / PurePosixPath(subpath)))
        cmd.append(f"{target_path}")
        cmd.append('−−no−perms')
        cmd = ' '.join(cmd)

        if dry_run:
            return cmd
        else:
            return self.exec(cmd)

    def sync_period(self, startdate, enddate, dry_run=False):
        """
        Synchronize SMOS L2 data between local root and FTP folder for days
        in the passed time frame. The last day on the server is usually not yet
        complete (i.e. swath files are missing). This will NOT be synchronized.

        Parameters
        ----------
        startdate: str or datetime
            First day to download data for (if available)
        enddate: str or datetime
            Last day to download data for (if available)

        Returns:
        -------
        ret: list
            List of return values or commands (if dry_run was chosen)
        """
        startdate = pd.to_datetime(startdate)
        enddate = pd.to_datetime(enddate)

        df = pd.Series(index=pd.date_range(startdate, enddate, freq='D'),
                       data=1)

        ret = []

        for year, ys in df.groupby(df.index.year):
            for month, ms in ys.groupby(ys.index.month):
                if len(ms) == monthrange(year, month)[1]:  # complete month (fast)
                    r = self.sync(int(year), int(month), day=None, dry_run=dry_run)
                    ret.append(r)
                else:  # individual days (slow)
                    for dt in ms.index.values:
                        dt = pd.Timestamp(dt).to_pydatetime()
                        r = self.sync(dt.year, dt.month, dt.day, dry_run=dry_run)
                        ret.append(r)

        first_day, last_day = get_first_last_day_images(str(self.local_root))

        props = dict(comment="DO NOT CHANGE THIS FILE MANUALLY! Required for data update.",
                     first_day=str(first_day) if first_day is not None else None,
                     last_day=str(last_day) if last_day is not None else None,
                     last_update=str(datetime.now()))

        with open(os.path.join(self.local_root, 'overview.yml'), 'w') as f:
            yaml.dump(props, f, default_flow_style=False, sort_keys=False)

        return ret
