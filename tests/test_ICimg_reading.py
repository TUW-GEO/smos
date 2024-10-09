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

'''
Tests for reading the image datasets.
'''

from smos.smos_ic.interface_ic import SMOS_IC_Img, SMOS_IC_Ds
import os
import numpy as np
import numpy.testing as nptest
from datetime import datetime


def test_SMOS_IC_Img():
    fname = os.path.join(os.path.dirname(__file__),
                         'smos-test-data', 'L3_SMOS_IC', 'ASC', '2018',
                         'SM_RE06_MIR_CDF3SA_20180101T000000_20180101T235959_105_001_8.DBL.nc')
    assert os.path.isfile(fname)

    ds = SMOS_IC_Img(fname, parameters=['Soil_Moisture'], read_flags=None)
    image = ds.read(datetime(2018, 1, 1))
    assert list(image.data.keys()) == ['Soil_Moisture']

    assert image.data['Soil_Moisture'].shape == (584, 1388)
    # test for correct masking --> point without data
    nptest.assert_almost_equal(image.lon[425, 1237], 140.9654, 4)
    nptest.assert_almost_equal(image.lat[425, 1237], -27.17044, 4)
    assert np.isnan(image.data['Soil_Moisture'][425, 1237])
    # test for correct masking --> point with data
    nptest.assert_almost_equal(image.lon[355, 458], -61.08069, 4)
    nptest.assert_almost_equal(image.lat[355, 458], -12.55398, 4)
    nptest.assert_almost_equal(image.data['Soil_Moisture'][355, 458], 0.198517, 4)

    metadata_keys = [u'_FillValue',
                     u'long_name',
                     u'units',
                     'image_missing']

    for key in image.metadata['Soil_Moisture'].keys():
        assert (key in metadata_keys)


def test_SMOS_IC_Img_flatten():
    fname = os.path.join(os.path.dirname(__file__),
                         'smos-test-data', 'L3_SMOS_IC', 'ASC', '2018',
                         'SM_RE06_MIR_CDF3SA_20180101T000000_20180101T235959_105_001_8.DBL.nc')
    ds = SMOS_IC_Img(fname, parameters=['Soil_Moisture'], flatten=True)
    image = ds.read(datetime(2018, 1, 1))
    assert list(image.data.keys()) == ['Soil_Moisture']
    assert image.data['Soil_Moisture'].shape == (584 * 1388,)
    # test for correct masking --> point without data
    nptest.assert_almost_equal(image.lat[(584 - 426) * 1388 + 1237], -27.17044, 4)
    nptest.assert_almost_equal(image.lon[(584 - 426) * 1388 + 1237], 140.9654, 4)
    assert np.isnan(image.data['Soil_Moisture'][425 * 1388 + 1237])
    # test for correct masking --> point with data
    nptest.assert_almost_equal(image.lon[(584 - 356) * 1388 + 458], -61.08069, 4)
    nptest.assert_almost_equal(image.lat[(584 - 356) * 1388 + 458], -12.55398, 4)
    nptest.assert_almost_equal(image.data['Soil_Moisture'][(584 - 356) * 1388 + 458], 0.198517, 4)

    metadata_keys = [u'_FillValue',
                     u'long_name',
                     u'units',
                     'image_missing']

    assert sorted(metadata_keys) == sorted(
        list(image.metadata['Soil_Moisture'].keys()))


def test_SMOS_IC_DS():
    fname = os.path.join(os.path.dirname(__file__),
                         'smos-test-data', 'L3_SMOS_IC', 'ASC')
    ds = SMOS_IC_Ds(fname, parameters=['Soil_Moisture'], read_flags=(0, 1, 2))
    image = ds.read(timestamp=datetime(2018, 1, 1))
    assert list(image.data.keys()) == ['Soil_Moisture']
    assert image.data['Soil_Moisture'].shape == (584, 1388)
    # test for correct masking --> point without data
    nptest.assert_almost_equal(image.lon[425, 1237], 140.9654, 4)
    nptest.assert_almost_equal(image.lat[425, 1237], -27.17044, 4)
    assert np.isnan(image.data['Soil_Moisture'][425, 1237])
    # test for correct masking --> point with data
    nptest.assert_almost_equal(image.lon[355, 458], -61.08069, 4)
    nptest.assert_almost_equal(image.lat[355, 458], -12.55398, 4)
    nptest.assert_almost_equal(image.data['Soil_Moisture'][355, 458], 0.198517, 4)

    metadata_keys = [u'_FillValue',
                     u'long_name',
                     u'units',
                     'image_missing']

    for key in image.metadata['Soil_Moisture'].keys():
        assert (key in metadata_keys)


def test_SMOS_IC_ts_for_daterange():
    fname = os.path.join(os.path.dirname(__file__),
                         'smos-test-data', 'L3_SMOS_IC', 'ASC', '2018')
    ds = SMOS_IC_Ds(fname, parameters=['Soil_Moisture'], read_flags=(0, 1), flatten=True)

    tstamps = ds.tstamps_for_daterange(start_date=datetime(2018, 1, 1),
                                       end_date=datetime(2018, 1, 5))
    assert len(tstamps) == 5
    assert tstamps == [datetime(2018, 1, 1),
                       datetime(2018, 1, 2),
                       datetime(2018, 1, 3),
                       datetime(2018, 1, 4),
                       datetime(2018, 1, 5)]
