# -*- coding: utf-8 -*-
# The MIT License (MIT)
#
# Copyright (c) 2019,TU Wien
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import os
import numpy as np
import numpy.testing as nptest
import tempfile
from smos.smos_ic.reshuffle_ic import main
import glob
from netCDF4 import Dataset
import pytest
from smos.interface import SMOSTs
from datetime import timedelta
import pandas as pd
from pygeogrids.netcdf import load_grid
from smos.grid import EASE25CellGrid


def test_SMOS_IC_reshuffle_global():
    inpath = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "smos-test-data", "L3_SMOS_IC", "ASC")

    with tempfile.TemporaryDirectory() as ts_path:
        startdate = '2018-01-01'  # 1 day is missing, should be filled with nans
        enddate = '2018-01-03'
        parameters = ["--parameters", "Soil_Moisture", "Scene_Flags"]

        args = [inpath, ts_path, startdate, enddate] + \
               parameters + ['--only_good', False]

        main(args)
        assert len(glob.glob(os.path.join(ts_path, "*.nc"))) == 2449
        ds = SMOSTs(ts_path, ioclass_kws={'read_bulk': True}, drop_missing=False)
        ts = ds.read(-61.08069, -12.55398)  # this is the same point as in image test
        assert ts['Scene_Flags'].dtype == np.float64 # because we dont drop missing
        sm_values_should = np.array([0.193305, np.nan, np.nan], dtype=np.float32)
        nptest.assert_allclose(ts['Soil_Moisture'].values, sm_values_should, 4)
        ds.close()


def test_SMOS_IC_reshuffle_subset():
    inpath = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "smos-test-data", "L3_SMOS_IC", "ASC")
    with tempfile.TemporaryDirectory() as ts_path:
        startdate = '2018-01-01'  # 1 day is missing, should be filled with nans
        enddate = '2018-01-03'
        bbox = ['-11', '34', '43', '71']
        args = [inpath, ts_path, startdate, enddate] + \
               ['--only_good', 'False'] + ['--bbox', *bbox]

        main(args)
        assert len(glob.glob(os.path.join(ts_path, "*.nc"))) == 109
        ds = SMOSTs(ts_path, ioclass_kws={'read_bulk': True}, index_add_time=True,
                    drop_missing=True)

        ts = ds.read(20.36023, 47.682177)  # this is the same point as in image subset test
        assert ts.index[0] == ts.iloc[0]['_date'] + timedelta(seconds=int(ts.iloc[0]['UTC_Seconds']))
        timestamp0 = ts.index[0]
        nptest.assert_almost_equal(ts.loc[timestamp0, 'Soil_Moisture'], 0.3130991, 5)
        assert np.issubdtype(ts['Scene_Flags'].dtype, np.integer)
        assert np.issubdtype(ts['Soil_Moisture'].dtype, np.floating)
        ds.close()
        ds = SMOSTs(ts_path, ioclass_kws={'read_bulk': True},
                    index_add_time=False, drop_missing=False)
        ts = ds.read(-4.7, 56.9)
        nptest.assert_almost_equal(ts.loc['2018-01-01', 'Soil_Moisture'], 0.2158, 4)
        assert ts.loc['2018-01-01', 'Scene_Flags'] == 1.0
        assert np.isnan(ds.read(-4.7, 65)['Soil_Moisture'].iloc[0])

        ds.close()

def _assert_same_ts_for_land_gpis(ts_path_land, ts_path_all, bbox, reader=SMOSTs):
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
    ds_land = reader(ts_path_land, ioclass_kws={'read_bulk': True}, drop_missing=False)
    ds_all = reader(ts_path_all, ioclass_kws={'read_bulk': True}, drop_missing=False)
    n_valid = 0
    for gpi in gpis[::max(1, len(gpis) // 300)]:
        ts_land, ts_all = ds_land.read(int(gpi)), ds_all.read(int(gpi))
        pd.testing.assert_frame_equal(ts_land, ts_all)
        n_valid += int(ts_land.notna().any(axis=1).sum())
    ds_land.close()
    ds_all.close()
    assert n_valid > 0


def test_SMOS_IC_reshuffle_land_same_gpis():
    inpath = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "smos-test-data", "L3_SMOS_IC", "ASC")
    bbox = (5., 45., 15., 55.)
    with tempfile.TemporaryDirectory() as ts_path_land, \
            tempfile.TemporaryDirectory() as ts_path_all:
        args = ['2018-01-01', '2018-01-03', '--parameters', 'Soil_Moisture']
        main([inpath, ts_path_land] + args + ['--only_land', 'True'])
        main([inpath, ts_path_all] + args + ['--bbox', *[str(b) for b in bbox]])
        _assert_same_ts_for_land_gpis(ts_path_land, ts_path_all, bbox)


@pytest.mark.parametrize("startdate,imgbuffer", [
    ('2018-01-01', 1),  # missing image in its own buffer
    ('2018-01-02', 100),  # first image is missing
])
def test_SMOS_IC_reshuffle_missing_image_types(startdate, imgbuffer):
    # Empty images (2018-01-02 is missing) have the same data types as the
    # actual images, integer variables keep their type and are masked
    inpath = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "smos-test-data", "L3_SMOS_IC", "ASC")
    with tempfile.TemporaryDirectory() as ts_path:
        main([inpath, ts_path, startdate, '2018-01-03',
              '--parameters', 'Soil_Moisture', 'Scene_Flags', 'Days',
              '--bbox', '-11', '34', '43', '71',
              '--imgbuffer', str(imgbuffer)])
        f = sorted(glob.glob(os.path.join(ts_path, '*.nc')))[0]
        with Dataset(f) as ds:
            assert ds['Soil_Moisture'].dtype == np.float32
            assert ds['Scene_Flags'].dtype == np.int8
            assert ds['Days'].dtype == np.int32
        ds = SMOSTs(ts_path, ioclass_kws={'read_bulk': True},
                    drop_missing=False)
        ts = ds.read(20.36023, 47.682177)
        ds.close()
        assert ts.loc['2018-01-02'].isna().all()
        assert ts.loc['2018-01-03', 'Days'] == 6577
        assert ts.loc['2018-01-03', 'Scene_Flags'] == 0


def test_firstfile(monkeypatch):
    from smos.reshuffle import firstfile
    root = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "smos-test-data", "L3_SMOS_IC")
    with tempfile.TemporaryDirectory() as tmp:
        import shutil
        shutil.copytree(os.path.join(root, 'ASC'), os.path.join(tmp, 'ASC'))
        # other files are ignored
        with open(os.path.join(tmp, 'ASC', 'overview.yml'), 'w') as f:
            f.write('first_day: 2018-01-01')
        # relative paths work
        monkeypatch.chdir(tmp)
        f, variables = firstfile('ASC')
        assert f == os.path.join('ASC', '2018', 'SM_RE06_MIR_CDF3SA_20180101T000000_'
                                                '20180101T235959_106_001_8.DBL.nc')
        assert 'Soil_Moisture' in variables
        os.makedirs('empty')
        with pytest.raises(IOError):
            firstfile('empty')
