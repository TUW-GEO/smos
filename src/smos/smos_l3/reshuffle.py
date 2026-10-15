"""
Convert SMOS L3 images into time series (5x5 degree cell files in
OrthoMulti format, readable with `smos.smos_l3.interface_l3.SMOSL3Ts`).
"""
import os
from datetime import datetime, timedelta
import pandas as pd
import yaml

from repurpose.img2ts import Img2Ts
from smos.grid import EASE25CellGrid
from smos.misc import read_summary_yml, get_first_last_day_images
from smos.smos_l3.interface_l3 import SMOS_L3_Ds, SMOS_L3_Img


def _first_image(img_path):
    # Path to the first image file (sorted) under img_path
    for root, dirs, files in sorted(os.walk(img_path)):
        dirs.sort()
        for f in sorted(files):
            if f.endswith('.DBL.nc'):
                return os.path.join(root, f)
    raise IOError(f"No SMOS L3 image (.DBL.nc) found in {img_path}")


def _write_overview(ts_path, props):
    with open(os.path.join(ts_path, 'overview.yml'), 'w') as f:
        yaml.dump(props, f, default_flow_style=False, sort_keys=False)


def img2ts(img_path,
           ts_path,
           startdate=None,
           enddate=None,
           parameters=None,
           bbox=None,
           only_land=False,
           imgbuffer=100):
    """
    Convert SMOS L3 images of one product / orbit into time series.

    Parameters
    ----------
    img_path: str
        Local folder of one product and orbit, as created by the download
        program, e.g. /path/to/MIR_CLF3SA
    ts_path: str
        Local directory where the converted time series data will be stored.
    startdate: str or datetime, optional (default: None)
        First day of the available images that should be included in the
        time series. If None is passed, then the first available day is used.
    enddate: str or datetime, optional (default: None)
        Last day of the available images that should be included in the
        time series. If None is passed, then the last available day is used.
    parameters: list, optional (default: None)
        Variables to include. If None, all variables in the image files are
        used. Variables with a third dimension can be passed with suffix
        (e.g. Soil_Moisture_med) or without (all elements are included).
    bbox: tuple, optional (default: None)
        (min_lon, min_lat, max_lon, max_lat) of the area to convert. None
        means global.
    only_land: bool, optional (default: False)
        Only convert land points.
    imgbuffer: int, optional (default: 100)
        Number of images that are read into memory before writing time
        series. More images mean faster conversion but more memory usage.
    """
    first_day, last_day = get_first_last_day_images(img_path)

    start = pd.to_datetime(startdate).to_pydatetime() \
        if startdate is not None else first_day
    end = pd.to_datetime(enddate).to_pydatetime() \
        if enddate is not None else last_day

    if start is None or end is None:
        raise ValueError("No start and/or end date provided.")
    start = datetime(start.year, start.month, start.day)
    end = datetime(end.year, end.month, end.day)

    if os.path.isfile(os.path.join(ts_path, 'overview.yml')):
        props = read_summary_yml(ts_path)
        if start <= pd.to_datetime(props['last_day']).to_pydatetime():
            raise ValueError("Cannot prepend data to time series, or replace "
                             "existing values. Choose a different start date "
                             "or use `extend_ts`.")

    grid = EASE25CellGrid(bbox=bbox, only_land=only_land)

    # resolve the parameter names and time series attributes from one image
    img = SMOS_L3_Img(
        _first_image(img_path), parameters=parameters, flatten=True, grid=grid)
    _, ts_attributes = img._read_img()
    for v in ts_attributes.values():
        v.pop('image_missing', None)
    parameters = list(img.parameters)
    global_attr = img.get_global_attrs()

    ds = SMOS_L3_Ds(img_path, parameters=parameters, flatten=True, grid=grid)
    global_attr['product'] = f"MIR_{ds.product}{ds.orbit}"

    os.makedirs(ts_path, exist_ok=True)

    reshuffler = Img2Ts(
        input_dataset=ds,
        outputpath=ts_path,
        startdate=start,
        enddate=end,
        input_grid=grid.cut(),
        imgbuffer=imgbuffer,
        cellsize_lat=5.0,
        cellsize_lon=5.0,
        global_attr=global_attr,
        zlib=True,
        unlim_chunksize=1000,
        ts_attributes=ts_attributes)
    reshuffler.calc()

    props = {
        'comment':
            "DO NOT CHANGE THIS FILE MANUALLY! Required for data update.",
        'product':
            f"MIR_{ds.product}{ds.orbit}",
        'last_day':
            str(end.date()),
        'last_update':
            str(datetime.now()),
        'parameters': [str(p) for p in parameters],
        'bbox': [float(b) for b in bbox] if bbox is not None else None,
        'only_land':
            bool(only_land)
    }
    _write_overview(ts_path, props)


def extend_ts(img_path, ts_path, imgbuffer=100):
    """
    Append new image data to an existing time series record, created with
    `img2ts`. This uses the last_day from overview.yml in the time series
    directory to decide which date the update should start from and the
    available images to decide how many images can be appended.
    The same parameters and spatial subset as in the original time series
    are used.

    Parameters
    ----------
    img_path: str
        Local folder of one product and orbit, e.g. /path/to/MIR_CLF3SA
    ts_path: str
        Path where the converted time series are stored.
    imgbuffer: int, optional (default: 100)
        Number of images that are read into memory before writing time
        series.
    """
    if not os.path.isfile(os.path.join(ts_path, 'overview.yml')):
        raise ValueError("No overview.yml found in the time series directory."
                         "Please use img2ts / reshuffle for initial time "
                         f"series setup or provide overview.yml in {ts_path}.")

    props = read_summary_yml(ts_path)
    startdate = pd.to_datetime(props['last_day']).to_pydatetime() + \
        timedelta(days=1)
    _, last_day = get_first_last_day_images(img_path)

    if last_day is None:
        raise ValueError(f"No images found in {img_path}")
    last_day = pd.to_datetime(last_day).to_pydatetime()

    if startdate > last_day:
        print(f"No extension required From: {startdate} To: {last_day}")
        return

    print(f"Extend time series data From: {startdate}, To: {last_day}")

    grid = EASE25CellGrid(
        bbox=tuple(props['bbox']) if props.get('bbox') is not None else None,
        only_land=props.get('only_land', False))
    ds = SMOS_L3_Ds(
        img_path, parameters=props['parameters'], flatten=True, grid=grid)

    reshuffler = Img2Ts(
        input_dataset=ds,
        outputpath=ts_path,
        startdate=startdate,
        enddate=last_day,
        input_grid=grid.cut(),
        imgbuffer=imgbuffer,
        cellsize_lat=5.0,
        cellsize_lon=5.0,
        zlib=True,
        unlim_chunksize=1000)
    reshuffler.calc()

    props['last_day'] = str(last_day.date())
    props['last_update'] = str(datetime.now())
    _write_overview(ts_path, props)
