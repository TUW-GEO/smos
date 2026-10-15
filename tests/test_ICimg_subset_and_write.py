# -*- coding: utf-8 -*-
# The MIT License (MIT)
#
# Copyright (c) 2020,TU Wien
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

"""
Tests for storing subset images.
"""

from smos.smos_ic.interface_ic import SMOS_IC_Ds
import os
import numpy as np
import numpy.testing as nptest
from datetime import datetime
from tempfile import mkdtemp
from smos.grid import EASE25CellGrid
import pytest


@pytest.mark.parametrize("stackfile,files", [(None, 2), ("stack.nc", 1)])
def test_SMOS_IC_Ds_subset(stackfile, files):
    # test reading and storing a spatial subset (as stack/single img)
    dsname = os.path.join(os.path.dirname(__file__),
                          'smos-test-data', 'L3_SMOS_IC', 'ASC')
    subgrid = EASE25CellGrid(bbox=(-11., 34., 43., 71.))
    params = ['Soil_Moisture', 'Scene_Flags']

    ds = SMOS_IC_Ds(dsname, parameters=params, grid=subgrid)
    image = ds.read(datetime(2018, 1, 1))

    # europe subset
    assert image.data['Soil_Moisture'].shape == (113, 208)
    assert list(image.data.keys()) == params

    # v106 data is pre-screened, only moderate topography (1) is kept
    valid = np.isfinite(image.data['Soil_Moisture'])
    assert sorted(np.unique(image.data['Scene_Flags'][valid])) == [0, 1]

    # index in global file [508, 772]
    nptest.assert_almost_equal(image.data['Soil_Moisture'][60, 120], 0.313099, decimal=4)
    nptest.assert_almost_equal(image.lon[60, 120], 20.36023, decimal=4)
    nptest.assert_almost_equal(image.lat[60, 120], 47.682177, decimal=4)

    nptest.assert_almost_equal(image.lon[25, 130], 22.95389, 4)
    nptest.assert_almost_equal(image.lat[25, 130], 59.1181825, 4)
    assert np.isnan(image.data['Soil_Moisture'][25, 130])
    assert np.ma.is_masked(image.data['Scene_Flags'][25, 130])

    # the output folder is created if it does not exist
    outdir = os.path.join(mkdtemp(), 'new', 'folder')
    ds.write_multiple(root_path=outdir, start_date=datetime(2018, 1, 1),
                      end_date=datetime(2018, 1, 3), stackfile=stackfile)

    if stackfile is None:
        assert os.path.isdir(os.path.join(outdir, '2018'))
        assert len(os.listdir(os.path.join(outdir, '2018'))) == 2  # Jan 2nd has no data
    else:
        ds.write_multiple(root_path=outdir, start_date=datetime(2018, 1, 1),
                          end_date=datetime(2018, 1, 3), stackfile=stackfile)
        assert len(os.listdir(outdir)) == 1  # 1 stack
