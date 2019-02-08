# -*- coding: utf-8 -*-
import os
import numpy as np
nptest = np.testing
import tempfile
from smos.reshuffle import main
import glob
from smos.interface import SMOSTs
import shutil


def test_SMOS_IC_reshuffle():

    inpath = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "smos-test-data", "L3_SMOS_IC")
    ts_path = tempfile.mkdtemp()
    startdate = '2018-01-01' # 1 day is missing, should be filled with nans
    enddate = '2018-01-03'
    parameters = ["--parameters","Soil_Moisture"]

    args = [inpath, ts_path, startdate, enddate] + \
           parameters + ['--only_good', False] + ['--filter_physical', False]

    main(args)
    assert len(glob.glob(os.path.join(ts_path, "*.nc"))) == 2449
    ds = SMOSTs(ts_path, ioclass_kws={'read_bulk':True})
    ts = ds.read(-61.08069, -12.55398) # this is the same point as in image test
    sm_values_should = np.array([0.198517, np.nan,  np.nan], dtype=np.float32)
    nptest.assert_allclose(ts['Soil_Moisture'].values, sm_values_should, 4)

    ds.close()
    shutil.rmtree(ts_path)

if __name__ == '__main__':
    test_SMOS_IC_reshuffle()