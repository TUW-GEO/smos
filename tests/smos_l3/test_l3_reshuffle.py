import os
import glob
from datetime import datetime, timedelta
from tempfile import TemporaryDirectory

import numpy as np
import pandas as pd
import pytest
from click.testing import CliRunner

from smos.grid import EASE25CellGrid
from smos.misc import read_summary_yml
from smos.smos_l3.interface_l3 import SMOS_L3_Ds, SMOSL3Ts
from smos.smos_l3.reshuffle import img2ts, extend_ts
from smos.smos_l3.cli import cli_reshuffle, cli_update_ts
from pygeogrids.netcdf import load_grid

BBOX = (5., 45., 15., 55.)  # small subset over central Europe
BBOX_SOUTH = (130., -30., 140., -20.)  # Australia, no frozen soil in January
DATES = [datetime(2021, 6, d) for d in (6, 7, 8, 9)]  # 8th is missing


def _compare_ts_with_images(img_path, ts_path, dates, bbox=BBOX):
    """
    Read all time series in ts_path and compare them for every location,
    variable and date to the image values. Returns the number of compared
    valid values.
    """
    props = read_summary_yml(ts_path)
    grid = EASE25CellGrid(bbox=bbox)
    ds = SMOS_L3_Ds(
        img_path, parameters=props['parameters'], flatten=True, grid=grid)
    images = {d: ds.read(d) for d in dates}
    ts_reader = SMOSL3Ts(
        ts_path, ioclass_kws={'read_bulk': True}, drop_missing=False)

    n_valid = 0
    for i, gpi in enumerate(grid.activegpis):
        ts = ts_reader.read(int(gpi))
        assert list(ts.index) == dates
        for d in dates:
            for p in props['parameters']:
                img_val = images[d].data[p][i]
                img_val = np.nan if np.ma.is_masked(img_val) else float(
                    img_val)
                ts_val = float(ts.loc[d, p])
                if np.isnan(img_val):
                    assert np.isnan(ts_val), (gpi, d, p, ts_val)
                else:
                    assert ts_val == pytest.approx(img_val, abs=1e-6), \
                        (gpi, d, p, img_val, ts_val)
                    n_valid += 1
    ts_reader.close()
    return n_valid


def test_img2ts_same_values_as_images(l3_root):
    img_path = os.path.join(l3_root, 'MIR_CLF3SA')
    with TemporaryDirectory() as ts_path:
        img2ts(
            img_path,
            ts_path,
            startdate='2021-06-06',
            enddate='2021-06-09',
            bbox=BBOX)
        props = read_summary_yml(ts_path)
        assert props['product'] == 'MIR_CLF3SA'
        assert props['last_day'] == '2021-06-09'
        assert len(props['parameters']) == 15
        assert len(glob.glob(os.path.join(ts_path,
                                          '*.nc'))) == 5  # 2x2 cells + grid

        n_valid = _compare_ts_with_images(img_path, ts_path, DATES)
        assert n_valid > 10000

        # missing day is all NaN
        ts = SMOSL3Ts(ts_path, drop_missing=False).read(10., 50.)
        assert ts.loc['2021-06-08'].isna().all()
        assert np.isfinite(ts.loc['2021-06-07', 'Soil_Moisture'])

        # same point via lon/lat as in the image
        ds = SMOS_L3_Ds(
            img_path,
            parameters=['Soil_Moisture'],
            grid=EASE25CellGrid(bbox=BBOX))
        img = ds.read(datetime(2021, 6, 7))
        r, c = np.argwhere(np.isfinite(img.data['Soil_Moisture']))[0]
        ts = SMOSL3Ts(ts_path).read(img.lon[r, c], img.lat[r, c])
        assert ts.loc['2021-06-07', 'Soil_Moisture'] == \
            pytest.approx(img.data['Soil_Moisture'][r, c], abs=1e-6)

        # prepending / overwriting is not possible
        with pytest.raises(ValueError):
            img2ts(img_path, ts_path, startdate='2021-06-06', bbox=BBOX)


def test_ts_observation_time(l3_root):
    img_path = os.path.join(l3_root, 'MIR_CLF3SA')
    with TemporaryDirectory() as ts_path:
        img2ts(
            img_path,
            ts_path,
            startdate='2021-06-06',
            enddate='2021-06-09',
            bbox=BBOX,
            parameters=[
                'Soil_Moisture', 'Mean_Acq_Time_Days', 'Mean_Acq_Time_Seconds'
            ])
        # the location with the most observations (revisit is 2-3 days)
        grid = EASE25CellGrid(bbox=BBOX)
        ds = SMOS_L3_Ds(
            img_path, parameters='Soil_Moisture', flatten=True, grid=grid)
        n_obs = np.sum(
            [np.isfinite(ds.read(d).data['Soil_Moisture']) for d in DATES],
            axis=0)
        gpi = int(grid.activegpis[np.argmax(n_obs)])
        assert n_obs.max() >= 2

        ts = SMOSL3Ts(ts_path, index_add_time=True).read(gpi)
        assert len(ts) == n_obs.max()
        for t, row in ts.iterrows():
            # observation time on the day of the image (6 am overpass)
            assert t.date() == row['_date'].date()
            assert t == datetime(2000, 1, 1) + timedelta(
                days=int(row['Mean_Acq_Time_Days']),
                seconds=int(row['Mean_Acq_Time_Seconds']))
            assert 3 <= t.hour <= 8


def test_extend_ts(l3_root):
    img_path = os.path.join(l3_root, 'MIR_CLF3SA')
    with TemporaryDirectory() as ts_path:
        img2ts(
            img_path,
            ts_path,
            startdate='2021-06-06',
            enddate='2021-06-07',
            bbox=BBOX,
            parameters=['Soil_Moisture', 'Science_Flags'])
        assert read_summary_yml(ts_path)['last_day'] == '2021-06-07'

        extend_ts(img_path, ts_path)
        props = read_summary_yml(ts_path)
        assert props['last_day'] == '2021-06-09'
        assert props['parameters'] == ['Soil_Moisture', 'Science_Flags']

        # extended time series are the same as the images (no duplicates)
        assert _compare_ts_with_images(img_path, ts_path, DATES) > 1000

        # nothing to do
        extend_ts(img_path, ts_path)
        assert read_summary_yml(ts_path)['last_day'] == '2021-06-09'

    with TemporaryDirectory() as ts_path:
        with pytest.raises(ValueError):
            extend_ts(img_path, ts_path)


@pytest.mark.parametrize("folder,enddate,dates", [
    ('MIR_CLF3DA', '2025-01-31',
     [datetime(2025, 1, 1),
      datetime(2025, 1, 11),
      datetime(2025, 1, 21)]),
    ('MIR_CLF3MA', '2025-02-28', [datetime(2025, 1, 1),
                                  datetime(2025, 2, 1)]),
])
def test_img2ts_dekad_and_monthly(l3_root, folder, enddate, dates):
    img_path = os.path.join(l3_root, folder)
    with TemporaryDirectory() as ts_path:
        img2ts(
            img_path,
            ts_path,
            startdate='2025-01-01',
            enddate=enddate,
            bbox=BBOX_SOUTH,
            parameters=['Soil_Moisture'])
        # only image time stamps of the product, test data has only the
        # first one, the others are missing (NaN)
        ts = SMOSL3Ts(ts_path, drop_missing=False).read(135., -25.)
        assert list(ts.index) == dates
        assert _compare_ts_with_images(
            img_path, ts_path, dates, bbox=BBOX_SOUTH) > 100


def test_cli_reshuffle_and_update(l3_root):
    img_path = os.path.join(l3_root, 'MIR_CLF3SA')
    with TemporaryDirectory() as ts_path:
        r = CliRunner().invoke(cli_reshuffle, [
            img_path, ts_path, '-s', '2021-06-06', '-e', '2021-06-07', '-v',
            'Soil_Moisture, Chi_2', '--bbox', *[str(b) for b in BBOX]
        ])
        assert r.exit_code == 0, r.output
        props = read_summary_yml(ts_path)
        assert props['parameters'] == ['Soil_Moisture', 'Chi_2']
        assert props['bbox'] == list(BBOX)

        r = CliRunner().invoke(cli_update_ts, [img_path, ts_path])
        assert r.exit_code == 0, r.output
        ts = SMOSL3Ts(ts_path, drop_missing=False).read(10., 50.)
        assert list(ts.index) == DATES
        assert list(ts.columns) == ['Soil_Moisture', 'Chi_2']


def _assert_same_ts_for_land_gpis(ts_path_land,
                                  ts_path_all,
                                  bbox,
                                  reader=SMOSL3Ts):
    # Land-only time series (global) and time series of all points (in bbox)
    # must contain the same data when read by the same gpi.
    grid_land = load_grid(os.path.join(ts_path_land, 'grid.nc'))
    grid_all = load_grid(os.path.join(ts_path_all, 'grid.nc'))
    gpis = np.intersect1d(grid_land.activegpis, grid_all.activegpis)
    assert len(gpis) > 100
    # land gpis are global gpis (not renumbered)
    assert grid_land.activegpis.max() > len(grid_land.activegpis)
    land_in_bbox = EASE25CellGrid(only_land=True, bbox=bbox).activegpis
    np.testing.assert_array_equal(np.sort(gpis), np.sort(land_in_bbox))
    ds_land = reader(
        ts_path_land, ioclass_kws={'read_bulk': True}, drop_missing=False)
    ds_all = reader(
        ts_path_all, ioclass_kws={'read_bulk': True}, drop_missing=False)
    n_valid = 0
    for gpi in gpis[::max(1, len(gpis) // 300)]:
        ts_land, ts_all = ds_land.read(int(gpi)), ds_all.read(int(gpi))
        pd.testing.assert_frame_equal(ts_land, ts_all)
        n_valid += int(ts_land.notna().any(axis=1).sum())
    ds_land.close()
    ds_all.close()
    assert n_valid > 0


def test_img2ts_land_same_gpis(l3_root):
    img_path = os.path.join(l3_root, 'MIR_CLF3SA')
    with TemporaryDirectory() as ts_path_land, \
            TemporaryDirectory() as ts_path_all:
        kwargs = dict(
            startdate='2021-06-06',
            enddate='2021-06-09',
            parameters=['Soil_Moisture', 'Science_Flags'])
        img2ts(img_path, ts_path_land, only_land=True, **kwargs)
        img2ts(img_path, ts_path_all, bbox=BBOX, **kwargs)
        _assert_same_ts_for_land_gpis(ts_path_land, ts_path_all, BBOX)
