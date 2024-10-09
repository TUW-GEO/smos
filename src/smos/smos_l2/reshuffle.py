import pandas as pd
import os
import yaml
from qa4sm_preprocessing.level2.smos import SMOSL2Reader
from smos.smos_l2.download import get_avail_img_range
from datetime import datetime

def read_summary_yml(path: str) -> dict:
    """
    Read image summary and return fields as dict.
    """
    path = os.path.join(path, 'overview.yml')

    with open(path, 'r') as stream:
        props = yaml.safe_load(stream)

    return props


def swath2ts(img_path, ts_path, startdate=None, enddate=None, memory=4):
    """
    Convert SMOS L2 swath data to time series in IndexedRaggedTs format.

    Parameters
    ----------
    img_path: str
        Local (root) directory where the annual folder containing SMOS L2 SM
        swath data are found.
    ts_path: str
        Local directory where the converted time series data will be stored.
    startdate: str or datetime, optional (default: None)
        First day of the available swath data that should be included in the
        time series. If None is passed, then the first available day is used.
    enddate: str or datetime, optional (default: None)
        Last day of the available swath data that should be included in the
        time series. If None is passed, then the last available day is used.
    memory : float, optional (default: 4)
        Size of available memory in GB. More memory will lead to a faster
        conversion.
    """
    reader = SMOSL2Reader(img_path)

    first_day, last_day = get_avail_img_range(img_path)

    start = pd.to_datetime(startdate).to_pydatetime() if startdate is not None else first_day
    end = pd.to_datetime(enddate).to_pydatetime() if enddate is not None else last_day

    out_file = os.path.join(ts_path, f"overview.yml")

    if os.path.isfile(out_file):
        props = read_summary_yml(ts_path)
        if start < pd.to_datetime(props['enddate']).to_pydatetime():
            raise ValueError("Cannot prepend data to time series, or replace "
                             "existing values. Choose different start date.")

    props = {'enddate': str(end), 'last_update': str(datetime.now()),
             'parameters': [str(v) for v in reader.varnames]}

    r = reader.repurpose(
        outpath=ts_path,
        start=start,
        end=end,
        memory=memory,
        overwrite=False,
        imgbaseconnection=True,
    )

    if r is not None:
        with open(out_file, 'w') as f:
            yaml.dump(props, f, default_flow_style=False, sort_keys=False)

def extend_ts(img_path, ts_path, memory=4):
    """
    Append new image data to an existing time series record.
    This will use the enddate from summary.yml in the time series
    directory to decide which date the update should start from and
    the available image directories to decide how many images can be
    appended.

    Parameters
    ----------
    img_path: str
        Path where the annual folders containing downloaded SMOS L2 images
        are stored
    ts_path: str
        Path where the converted time series (initially created using the
        reshuffle / swath2ts command) are stored.
    memory: int, optional (default: 4)
        Available memory in GB
    """
    out_file = os.path.join(ts_path, f"overview.yml")
    if not os.path.isfile(out_file):
        raise ValueError("No overview.yml found in the time series directory."
                         "Please use reshuffle / swath2ts for initial time "
                         f"series setup or provide overview.yml in {ts_path}.")

    props = read_summary_yml(ts_path)
    startdate = pd.to_datetime(props['enddate']).to_pydatetime()
    _, enddate = get_avail_img_range(img_path)

    reader = SMOSL2Reader(img_path)

    print(f"From: {startdate}, To: {enddate}")

    r = reader.repurpose(
        outpath=ts_path,
        start=startdate,
        end=enddate,
        memory=memory,
        imgbaseconnection=True,
        overwrite=False,
        append=True,
    )

    if r is not None:
        props['enddate'] = str(enddate)
        props['last_update'] = str(datetime.now())

        with open(out_file, 'w') as f:
            yaml.dump(props, f, default_flow_style=False, sort_keys=False)
