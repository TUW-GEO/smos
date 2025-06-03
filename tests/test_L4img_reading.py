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

from smos.smos_l4.interface_l4 import SMOS_L4_Img, SMOS_L4_Ds
import os
import numpy as np
import numpy.testing as nptest
from datetime import datetime


def test_SMOSL4_Img():
    fname = os.path.join(os.path.dirname(__file__),
                         'smos-test-data', 'L4_SMOS_RZSM', 'SCIE', '2018',
                         'SM_SCIE_MIR_CLF4RD_20180101T000000_20180101T235959_301_001_9.DBL.nc')
    ds = SMOS_L4_Img(fname, parameters=['RZSM'])
    image = ds.read(datetime(2018, 1, 1))
    assert list(image.data.keys()) == ['RZSM']
    assert image.data['RZSM'].shape == (584, 1388)
    # test for correct masking --> point without data
    nptest.assert_almost_equal(image.lon[469, 973], 72.4928, 4)
    nptest.assert_almost_equal(image.lat[469, 973], -37.35189, 4)
    assert np.isnan(image.data['RZSM'][469, 973])
    # test for correct masking --> point with data
    nptest.assert_almost_equal(image.lon[416, 1236], 140.7061, 4)
    nptest.assert_almost_equal(image.lat[416, 1236], -25.20802, 4)
    nptest.assert_almost_equal(image.data['RZSM'][416, 1236], 0.090486, 4)

    metadata_keys = [u'_FillValue',
                     u'long_name',
                     u'units',
                     'image_missing']

    for key in image.metadata['RZSM'].keys():
        assert (key in metadata_keys)


def test_SMOSL4_Img_flatten():
    fname = os.path.join(os.path.dirname(__file__),
                         'smos-test-data', 'L4_SMOS_RZSM', 'SCIE', '2018',
                         'SM_SCIE_MIR_CLF4RD_20180101T000000_20180101T235959_301_001_9.DBL.nc')
    ds = SMOS_L4_Img(fname, parameters=['RZSM'], flatten=True)
    image = ds.read(datetime(2018, 1, 1))
    assert list(image.data.keys()) == ['RZSM']
    assert image.data['RZSM'].shape == (584 * 1388,)
    # test for correct masking --> point without data
    nptest.assert_almost_equal(image.lat[(584 - 426) * 1388 + 1237], -27.17044, 4)
    nptest.assert_almost_equal(image.lon[(584 - 426) * 1388 + 1237], 140.9654, 4)
    assert np.isnan(image.data['RZSM'][425 * 1388 + 1237])
    # test for correct masking --> point with data
    nptest.assert_almost_equal(image.lon[(584 - 505) * 1388 + 420], -70.936599, 4)
    nptest.assert_almost_equal(image.lat[(584 - 505) * 1388 + 420], -46.537532, 4)
    nptest.assert_almost_equal(image.data['RZSM'][(584 - 505) * 1388 + 420], 0.104644, 4)

    metadata_keys = [u'_FillValue',
                     u'long_name',
                     u'units',
                     'image_missing']

    assert sorted(metadata_keys) == sorted(
        list(image.metadata['RZSM'].keys()))


def test_SMOSL4_DS():
    fname = os.path.join(os.path.dirname(__file__),
                         'smos-test-data', 'L4_SMOS_RZSM', 'SCIE')
    ds = SMOS_L4_Ds(fname, parameters=['RZSM'])
    image = ds.read(timestamp=datetime(2018, 1, 1))
    assert list(image.data.keys()) == ['RZSM']
    assert image.data['RZSM'].shape == (584, 1388)
    # test for correct masking --> point without data
    nptest.assert_almost_equal(image.lon[469, 973], 72.4928, 4)
    nptest.assert_almost_equal(image.lat[469, 973], -37.35189, 4)
    assert np.isnan(image.data['RZSM'][469, 973])
    # test for correct masking --> point with data
    nptest.assert_almost_equal(image.lon[150, 285], -105.9510086, 4)
    nptest.assert_almost_equal(image.lat[150, 285], 28.9435427, 4)
    nptest.assert_almost_equal(image.data['RZSM'][150, 285], 0.12537476, 4)

    metadata_keys = [u'_FillValue',
                     u'long_name',
                     u'units',
                     'image_missing']

    for key in image.metadata['RZSM'].keys():
        assert (key in metadata_keys)


def test_SMOSL4_ts_for_daterange():
    ds = SMOS_L4_Ds('', parameters=['RZSM'], flatten=True)

    tstamps = ds.tstamps_for_daterange(start_date=datetime(2018, 1, 1),
                                       end_date=datetime(2018, 1, 5))
    assert len(tstamps) == 5
    assert tstamps == [datetime(2018, 1, 1),
                       datetime(2018, 1, 2),
                       datetime(2018, 1, 3),
                       datetime(2018, 1, 4),
                       datetime(2018, 1, 5)]


def test_SMOSL4OPER_Img():
    fname = os.path.join(os.path.dirname(__file__),
                         'smos-test-data', 'L4_SMOS_RZSM', 'OPER', '2020',
                         'SM_OPER_MIR_CLF4RD_20200131T000000_20200131T235959_300_001_9.DBL.nc')
    print(fname)
    ds = SMOS_L4_Img(fname, parameters=['RZSM'], oper=True)
    image = ds.read(datetime(2020, 1, 31))
    assert list(image.data.keys()) == ['RZSM']
    assert image.data['RZSM'].shape == (584, 1388)
    # test for correct masking --> point without data
    nptest.assert_almost_equal(image.lon[469, 973], 72.4928, 4)
    nptest.assert_almost_equal(image.lat[469, 973], -37.35189, 4)
    assert np.isnan(image.data['RZSM'][469, 973])
    # test for correct masking --> point with data
    nptest.assert_almost_equal(image.lon[416, 1236], 140.7061, 4)
    nptest.assert_almost_equal(image.lat[416, 1236], -25.20802, 4)
    nptest.assert_almost_equal(image.data['RZSM'][416, 1236], 0.10248116, 4)

    metadata_keys = [u'_FillValue',
                     u'long_name',
                     u'units',
                     'image_missing']

    for key in image.metadata['RZSM'].keys():
        assert (key in metadata_keys)


def test_SMOSL4OPER_Img_flatten():
    fname = os.path.join(os.path.dirname(__file__),
                         'smos-test-data', 'L4_SMOS_RZSM', 'OPER', '2020',
                         'SM_OPER_MIR_CLF4RD_20200131T000000_20200131T235959_300_001_9.DBL.nc')
    ds = SMOS_L4_Img(fname, parameters=['RZSM'], flatten=True, oper=True)
    image = ds.read(datetime(2020, 1, 31))
    assert list(image.data.keys()) == ['RZSM']
    assert image.data['RZSM'].shape == (584 * 1388,)
    # test for correct masking --> point without data
    nptest.assert_almost_equal(image.lat[(584 - 426) * 1388 + 1237], -27.17044, 4)
    nptest.assert_almost_equal(image.lon[(584 - 426) * 1388 + 1237], 140.9654, 4)
    assert np.isnan(image.data['RZSM'][425 * 1388 + 1237])
    # test for correct masking --> point with data
    nptest.assert_almost_equal(image.lon[(584 - 356) * 1388 + 458], -61.08069, 4)
    nptest.assert_almost_equal(image.lat[(584 - 356) * 1388 + 458], -12.55398, 4)
    nptest.assert_almost_equal(image.data['RZSM'][(584 - 356) * 1388 + 458], 0.1866512, 4)

    metadata_keys = [u'_FillValue',
                     u'long_name',
                     u'units',
                     'image_missing']

    assert sorted(metadata_keys) == sorted(
        list(image.metadata['RZSM'].keys()))


def test_SMOSL4OPER_DS():
    fname = os.path.join(os.path.dirname(__file__),
                         'smos-test-data', 'L4_SMOS_RZSM', 'OPER')
    ds = SMOS_L4_Ds(fname, parameters=['RZSM'], oper=True)
    image = ds.read(timestamp=datetime(2020, 1, 31))
    assert list(image.data.keys()) == ['RZSM']
    assert image.data['RZSM'].shape == (584, 1388)
    # test for correct masking --> point without data
    nptest.assert_almost_equal(image.lon[469, 973], 72.4928, 4)
    nptest.assert_almost_equal(image.lat[469, 973], -37.35189, 4)
    assert np.isnan(image.data['RZSM'][469, 973])
    # test for correct masking --> point with data
    nptest.assert_almost_equal(image.lon[355, 458], -61.08069, 4)
    nptest.assert_almost_equal(image.lat[355, 458], -12.55398, 4)
    nptest.assert_almost_equal(image.data['RZSM'][355, 458], 0.1866512, 4)

    metadata_keys = [u'_FillValue',
                     u'long_name',
                     u'units',
                     'image_missing']

    for key in image.metadata['RZSM'].keys():
        assert (key in metadata_keys)


def test_SMOSL4OPER_ts_for_daterange():
    ds = SMOS_L4_Ds('', parameters=['RZSM'], flatten=True, oper=True)

    tstamps = ds.tstamps_for_daterange(start_date=datetime(2018, 1, 1),
                                       end_date=datetime(2018, 1, 5))
    assert len(tstamps) == 5
    assert tstamps == [datetime(2018, 1, 1),
                       datetime(2018, 1, 2),
                       datetime(2018, 1, 3),
                       datetime(2018, 1, 4),
                       datetime(2018, 1, 5)]

if __name__ == '__main__':
    test_SMOSL4OPER_DS()