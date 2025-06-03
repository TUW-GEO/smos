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
from smos.smos_l4.reshuffle_l4 import main
import glob
from smos.interface import SMOSTs

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
        assert ts['QUAL'].dtype == float # because we dont drop missing
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
        # Test a known land point
        ds = SMOSTs(ts_path_land, ioclass_kws={'read_bulk': True}, drop_missing=False)
        ts = ds.read(26.2, 6.3) 
        timestamp0 = ts.index[0]
        nptest.assert_almost_equal(ts.loc[timestamp0, 'RZSM'], 0.337183, 4)
        assert ts['QUAL'].dtype == float
        assert ts['RZSM'].dtype == float
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
        assert ts['QUAL'].dtype == float
        assert ts['RZSM'].dtype == float
        ds.close()
        ds = SMOSTs(ts_path, drop_missing=False, ioclass_kws={'read_bulk': True})
        ts = ds.read(-61.08069, -12.55398)
        assert np.isnan(ts.loc['2018-01-01', 'RZSM'])
        assert np.isnan(ts.loc['2018-01-01', 'QUAL'])
        ds.close()