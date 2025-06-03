import numpy as np
import pandas as pd
import os
import yaml
from qa4sm_preprocessing.level2.smos import SMOSL2Reader
from smos.misc import read_summary_yml, get_first_last_day_images
from datetime import datetime

_default_variables = (
    "Soil_Moisture",
    "Science_Flags",
    "Confidence_Flags",
    "Chi_2_P",
    "RFI_Prob",
    "N_RFI_X",
    "N_RFI_Y",
    "M_AVA0",
)

def swath2ts(img_path, ts_path, variables=_default_variables,
             startdate=None, enddate=None, memory=4, only_land=False):
    """
    Convert SMOS L2 swath data to time series in IndexedRaggedTs format.

    Parameters
    ----------
    img_path: str
        Local (root) directory where the annual folder containing SMOS L2 SM
        swath data are found.
    ts_path: str
        Local directory where the converted time series data will be stored.
    variables: tuple or str, optional (default: None)
        List of variables to include, None will use the default variables
        "Soil_Moisture",
        "Soil_Moisture_DQX",
        "Science_Flags",
        "Confidence_Flags",
        "Processing_Flags",
        "Chi_2_P",
        "RFI_Prob",
        "N_RFI_X",
        "N_RFI_Y",
        "M_AVA0",
        "acquisition_time"
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
    variables = [v for v in np.atleast_1d(variables)]

    if "acquisition_time" not in variables:
        variables.append("acquisition_time")

    reader = SMOSL2Reader(img_path, varnames=variables,
                          add_overpass_flag=True, only_land=only_land)

    first_day, last_day = get_first_last_day_images(img_path)

    start = pd.to_datetime(startdate).to_pydatetime() if startdate is not None else first_day
    end = pd.to_datetime(enddate).to_pydatetime() if enddate is not None else last_day

    if start is None or end is None:
        raise ValueError("No start and/or end date provided.")

    out_file = os.path.join(ts_path, f"overview.yml")

    if os.path.isfile(out_file):
        props = read_summary_yml(ts_path)
        if start < pd.to_datetime(props['last_day']).to_pydatetime():
            raise ValueError("Cannot prepend data to time series, or replace "
                             "existing values. Choose different start date.")

    props = {'comment': "DO NOT CHANGE THIS FILE MANUALLY! Required for data update.",
             'last_day': str(end), 'last_update': str(datetime.now()),
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

def extend_ts(img_path, ts_path, memory=4, only_land=False):
    """
    Append new image data to an existing time series record.
    This will use the last_day from summary.yml in the time series
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
    startdate = pd.to_datetime(props['last_day']).to_pydatetime()
    _, last_day = get_first_last_day_images(img_path)

    if startdate is None or last_day is None:
        raise ValueError("No start and/or end date provided.")

    startdate = pd.to_datetime(startdate).to_pydatetime()
    last_day = pd.to_datetime(last_day).to_pydatetime()

    if startdate < last_day:

        reader = SMOSL2Reader(img_path, only_land=only_land)

        print(f"Extent TimeSeries data From: {startdate}, To: {last_day}")

        r = reader.repurpose(
            outpath=ts_path,
            start=startdate,
            end=last_day,
            memory=memory,
            imgbaseconnection=True,
            overwrite=False,
            append=True,
        )

        if r is not None:
            props['last_day'] = str(last_day)
            props['last_update'] = str(datetime.now())

            with open(out_file, 'w') as f:
                yaml.dump(props, f, default_flow_style=False, sort_keys=False)

    else:
        print(f"No extension required From: {startdate} To: {last_day}")
