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
from smos.interface import SMOSTs
from datetime import timedelta


def test_SMOS_IC_reshuffle_global():
    inpath = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "smos-test-data", "L3_SMOS_IC", "ASC")

    with tempfile.TemporaryDirectory() as ts_path:
        startdate = '2018-01-01'  # 1 day is missing, should be filled with nans
        enddate = '2018-01-03'
        parameters = ["--parameters", "Soil_Moisture", "Quality_Flag"]

        args = [inpath, ts_path, startdate, enddate] + \
               parameters + ['--only_good', False]

        main(args)
        assert len(glob.glob(os.path.join(ts_path, "*.nc"))) == 2449
        ds = SMOSTs(ts_path, ioclass_kws={'read_bulk': True}, drop_missing=False)
        ts = ds.read(-61.08069, -12.55398)  # this is the same point as in image test
        assert ts['Quality_Flag'].dtype == np.float64 # because we dont drop missing
        sm_values_should = np.array([0.198517, np.nan, np.nan], dtype=np.float32)
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
        nptest.assert_almost_equal(ts.loc[timestamp0, 'Soil_Moisture'], 0.31218335)
        assert np.issubdtype(ts['Quality_Flag'].dtype, np.integer)
        assert np.issubdtype(ts['Soil_Moisture'].dtype, np.floating)
        ds.close()
        ds = SMOSTs(ts_path, ioclass_kws={'read_bulk': True},
                    index_add_time=False, drop_missing=False)
        ts = ds.read(-4.7, 56.9)
        nptest.assert_almost_equal(ts.loc['2018-01-01', 'Soil_Moisture'], 0.2196, 4)
        assert ts.loc['2018-01-01', 'Quality_Flag'] == 1.0
        assert np.isnan(ds.read(-4.7, 65)['Soil_Moisture'].iloc[0])

        ds.close()
