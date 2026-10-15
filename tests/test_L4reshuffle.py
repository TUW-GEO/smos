# -*- coding: utf-8 -*-
# The MIT License (MIT)
#
# Copyright (c) 2021,TU Wien
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
import pytest
from datetime import datetime
from smos.smos_l4.reshuffle_l4 import main
import glob
from netCDF4 import Dataset
from smos.interface import SMOSTs
import pandas as pd
from pygeogrids.netcdf import load_grid
from smos.grid import EASE25CellGrid

inpath = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "smos-test-data", "L4_SMOS_RZSM", "SCIE")

def test_SMOS_L4_reshuffle_global():
    with tempfile.TemporaryDirectory() as ts_path:
        startdate = '2018-01-01'  # 1 day is missing, should be filled with nans
        enddate = '2018-01-03'
        parameters = ["--parameters", "RZSM", "QUAL"]

        args = [inpath, ts_path, startdate, enddate] + \
               parameters + ['--only_good', False]

        main(args)
        assert len(glob.glob(os.path.join(ts_path, "*.nc"))) == 2449
        ds = SMOSTs(ts_path, ioclass_kws={'read_bulk': True}, drop_missing=False)
        ts = ds.read(150.625, -32.125)  # this is the same point as in image test
        assert ts['QUAL'].dtype == np.float32  # as in the image files, also for missing days
        sm_values_should = np.array([0.136741, 0.136160, np.nan], dtype=np.float32)
        nptest.assert_allclose(ts['RZSM'].values, sm_values_should, 4)
        ds.close()


def test_SMOS_L4_reshuffle_land_only():
    with tempfile.TemporaryDirectory() as ts_path_land:
        startdate = '2018-01-01'
        enddate = '2018-01-03'
        parameters = ["--parameters", "RZSM", "QUAL"]
        args_land = [inpath, ts_path_land, startdate, enddate] + \
                   parameters + ['--only_good', 'False'] + ['--only_land', 'True']

        main(args_land)
        assert len(glob.glob(os.path.join(ts_path_land, "*.nc"))) == 1134
        # Test a known land point (gpi 203068 in the global grid). Note: before
        # land points kept their global gpis, values of wrong pixels were read
        # for land-only grids (e.g. 0.337183 from Patagonia at 26.2, 6.3).
        ds = SMOSTs(ts_path_land, ioclass_kws={'read_bulk': True}, drop_missing=False)
        ts = ds.read(-70.9366, -29.8412)
        assert ts.equals(ds.read(203068))
        timestamp0 = ts.index[0]
        nptest.assert_almost_equal(ts.loc[timestamp0, 'RZSM'], 0.146774, 5)
        # value at this location in the image file
        with Dataset(glob.glob(os.path.join(inpath, '2018', '*20180101T*.nc'))[0]) as nc:
            nptest.assert_almost_equal(nc['RZSM'][:].flatten()[203068], 0.146774, 5)
        assert ts['QUAL'].dtype == np.float32
        assert ts['RZSM'].dtype == np.float32
        ds.close()



def test_SMOS_L4_reshuffle_subset():
    inpath = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "smos-test-data", "L4_SMOS_RZSM", "SCIE")
    with tempfile.TemporaryDirectory() as ts_path:
        startdate = '2018-01-01'  # 1 day is missing, should be filled with nans
        enddate = '2018-01-03'
        bbox = ['-11', '34', '43', '71']
        args = [inpath, ts_path, startdate, enddate] + \
               ['--only_good', 'False'] + ['--bbox', *bbox]# + ['--only_land', 'True']

        main(args)
        assert len(glob.glob(os.path.join(ts_path, "*.nc"))) == 109
        ds = SMOSTs(ts_path, drop_missing=False, ioclass_kws={'read_bulk': True})

        ts = ds.read(20.36023, 47.682177)
        timestamp0 = ts.index[0]
        nptest.assert_almost_equal(ts.loc[timestamp0, 'RZSM'], 0.248682, 4)
        assert ts['QUAL'].dtype == np.float32
        assert ts['RZSM'].dtype == np.float32
        ds.close()
        ds = SMOSTs(ts_path, drop_missing=False, ioclass_kws={'read_bulk': True})
        ts = ds.read(-61.08069, -12.55398)
        assert np.isnan(ts.loc['2018-01-01', 'RZSM'])
        assert np.isnan(ts.loc['2018-01-01', 'QUAL'])
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


def test_SMOS_L4_reshuffle_land_same_gpis():
    bbox = (20., 0., 30., 10.)
    with tempfile.TemporaryDirectory() as ts_path_land, \
            tempfile.TemporaryDirectory() as ts_path_all:
        args = ['2018-01-01', '2018-01-02', '--parameters', 'RZSM',
                '--only_good', 'False']
        main([inpath, ts_path_land] + args + ['--only_land', 'True'])
        main([inpath, ts_path_all] + args + ['--bbox', *[str(b) for b in bbox]])
        _assert_same_ts_for_land_gpis(ts_path_land, ts_path_all, bbox)


@pytest.mark.parametrize("only_good", [False, True])
def test_SMOS_L4_reshuffle_quality(only_good):
    # All quality levels are kept by default (QUAL 0.6, 0.8 and 1.0 in the
    # test data), only QUAL=1 with --only_good.
    from smos.smos_l4.interface_l4 import SMOS_L4_Img
    bbox = (-11., 34., 43., 71.)
    subgrid = EASE25CellGrid(bbox=bbox)
    fname = glob.glob(os.path.join(inpath, '2018', '*20180101T*.nc'))[0]
    img = SMOS_L4_Img(fname, parameters=['RZSM', 'QUAL'], flatten=True,
                      read_flags=None, grid=subgrid).read(datetime(2018, 1, 1))
    gpis = subgrid.activegpis
    with tempfile.TemporaryDirectory() as ts_path:
        main([inpath, ts_path, '2018-01-01', '2018-01-01',
              '--parameters', 'RZSM', 'QUAL', '--only_good', str(only_good),
              '--bbox', *[str(b) for b in bbox]])
        ds = SMOSTs(ts_path, ioclass_kws={'read_bulk': True},
                    drop_missing=False)
        for q in (0.6, 0.8, 1.0):
            idx = np.where(np.isclose(img.data['QUAL'], q))[0]
            assert len(idx) > 0
            for i in idx[::max(1, len(idx) // 20)]:
                ts = ds.read(int(gpis[i]))
                if q < 1 and only_good:
                    assert np.isnan(ts['RZSM'].iloc[0])
                else:
                    nptest.assert_almost_equal(ts['RZSM'].iloc[0],
                                               img.data['RZSM'][i], 5)
                    nptest.assert_almost_equal(ts['QUAL'].iloc[0], q, 5)
        ds.close()


def test_SMOS_L4OPER_reshuffle():
    # The operational product is detected from the files
    oper_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "smos-test-data", "L4_SMOS_RZSM", "OPER")
    with tempfile.TemporaryDirectory() as ts_path:
        main([oper_path, ts_path, '2020-01-31', '2020-01-31',
              '--parameters', 'RZSM', 'Quality', '--only_good', 'True',
              '--bbox', '-11', '34', '43', '71'])
        ds = SMOSTs(ts_path, ioclass_kws={'read_bulk': True},
                    drop_missing=False)
        grid = load_grid(os.path.join(ts_path, 'grid.nc'))
        quality = []
        for gpi in grid.activegpis[::50]:
            ts = ds.read(int(gpi))
            if np.isfinite(ts['RZSM'].iloc[0]):
                quality.append(ts['Quality'].iloc[0])
        ds.close()
        assert len(quality) > 0
        assert np.all(np.array(quality) == 1)
