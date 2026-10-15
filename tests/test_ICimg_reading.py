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
import shutil
import pytest
from tempfile import TemporaryDirectory


def test_SMOS_IC_Img():
    fname = os.path.join(os.path.dirname(__file__),
                         'smos-test-data', 'L3_SMOS_IC', 'ASC', '2018',
                         'SM_RE06_MIR_CDF3SA_20180101T000000_20180101T235959_106_001_8.DBL.nc')
    assert os.path.isfile(fname)

    ds = SMOS_IC_Img(fname, parameters=['Soil_Moisture'])
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
    nptest.assert_almost_equal(image.data['Soil_Moisture'][355, 458], 0.193305, 4)

    metadata_keys = [u'_FillValue',
                     u'long_name',
                     u'units',
                     'image_missing']

    for key in image.metadata['Soil_Moisture'].keys():
        assert (key in metadata_keys)


def test_SMOS_IC_Img_flatten():
    fname = os.path.join(os.path.dirname(__file__),
                         'smos-test-data', 'L3_SMOS_IC', 'ASC', '2018',
                         'SM_RE06_MIR_CDF3SA_20180101T000000_20180101T235959_106_001_8.DBL.nc')
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
    nptest.assert_almost_equal(image.data['Soil_Moisture'][(584 - 356) * 1388 + 458], 0.193305, 4)

    metadata_keys = [u'_FillValue',
                     u'long_name',
                     u'units',
                     'image_missing']

    assert sorted(metadata_keys) == sorted(
        list(image.metadata['Soil_Moisture'].keys()))


def test_SMOS_IC_DS():
    fname = os.path.join(os.path.dirname(__file__),
                         'smos-test-data', 'L3_SMOS_IC', 'ASC')
    ds = SMOS_IC_Ds(fname, parameters=['Soil_Moisture'])
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
    nptest.assert_almost_equal(image.data['Soil_Moisture'][355, 458], 0.193305, 4)

    metadata_keys = [u'_FillValue',
                     u'long_name',
                     u'units',
                     'image_missing']

    for key in image.metadata['Soil_Moisture'].keys():
        assert (key in metadata_keys)


def test_SMOS_IC_ts_for_daterange():
    fname = os.path.join(os.path.dirname(__file__),
                         'smos-test-data', 'L3_SMOS_IC', 'ASC', '2018')
    ds = SMOS_IC_Ds(fname, parameters=['Soil_Moisture'], flatten=True)

    tstamps = ds.tstamps_for_daterange(start_date=datetime(2018, 1, 1),
                                       end_date=datetime(2018, 1, 5))
    assert len(tstamps) == 5
    assert tstamps == [datetime(2018, 1, 1),
                       datetime(2018, 1, 2),
                       datetime(2018, 1, 3),
                       datetime(2018, 1, 4),
                       datetime(2018, 1, 5)]


def test_SMOS_IC_Img_no_quality_flag():
    fname = os.path.join(os.path.dirname(__file__),
                         'smos-test-data', 'L3_SMOS_IC', 'ASC', '2018',
                         'SM_RE06_MIR_CDF3SA_20180101T000000_20180101T235959_106_001_8.DBL.nc')
    # v106 files don't contain a Quality_Flag (anymore)
    ds = SMOS_IC_Img(fname)
    image = ds.read(datetime(2018, 1, 1))
    assert 'Quality_Flag' not in image.data.keys()
    assert 'Skin_Temperature_ECMWF' in image.data.keys()
    # fill values of integer variables are masked
    assert np.ma.is_masked(image.data['Scene_Flags'][425, 1237])
    assert image.data['Scene_Flags'][355, 458] == 0

    with pytest.raises(ValueError, match='Quality_Flag'):
        SMOS_IC_Img(fname, parameters=['Quality_Flag']).read(datetime(2018, 1, 1))


def test_SMOS_IC_Ds_version_selection():
    src = os.path.join(os.path.dirname(__file__),
                       'smos-test-data', 'L3_SMOS_IC', 'DES', '2018',
                       'SM_RE06_MIR_CDF3SD_20180101T000000_20180101T235959_106_001_8.DBL.nc')
    names = ['SM_RE06_MIR_CDF3SD_20180101T000000_20180101T235959_105_001_8.DBL.nc',
             'SM_RE06_MIR_CDF3SD_20180101T000000_20180101T235959_106_001_8.DBL.nc',
             'SM_OPER_MIR_CDF3SD_20180101T000000_20180101T235959_106_002_8.DBL.nc']
    with TemporaryDirectory() as tempdir:
        os.makedirs(os.path.join(tempdir, '2018'))
        for n in names:
            # same content, only the file name is relevant here
            shutil.copy(src, os.path.join(tempdir, '2018', n))

        # by default the latest version and file counter is used
        ds = SMOS_IC_Ds(tempdir, parameters=['Soil_Moisture'])
        image = ds.read(datetime(2018, 1, 1))
        assert os.path.basename(ds.fid.filename) == names[2]
        assert np.isfinite(image.data['Soil_Moisture']).any()

        ds = SMOS_IC_Ds(tempdir, parameters=['Soil_Moisture'], version=105)
        ds.read(datetime(2018, 1, 1))
        assert os.path.basename(ds.fid.filename) == names[0]

        ds = SMOS_IC_Ds(tempdir, parameters=['Soil_Moisture'], version='106')
        ds.read(datetime(2018, 1, 1))
        assert os.path.basename(ds.fid.filename) == names[2]


def _open_nc_files():
    # netCDF files opened by this process (Linux only)
    files = []
    for fd in os.listdir('/proc/self/fd'):
        try:
            path = os.readlink(os.path.join('/proc/self/fd', fd))
        except OSError:
            continue
        if path.endswith('.nc'):
            files.append(os.path.realpath(path))
    return files


@pytest.mark.skipif(not os.path.isdir('/proc/self/fd'),
                    reason="Checks open files via /proc (Linux)")
@pytest.mark.parametrize("product", ['IC', 'L4'])
def test_image_file_closed_after_reading(product):
    # Image files must be closed after reading, otherwise they can't be
    # deleted / moved on Windows while the reader object exists.
    from smos.smos_l4.interface_l4 import SMOS_L4_Ds
    testdata = os.path.join(os.path.dirname(__file__), 'smos-test-data')
    if product == 'IC':
        ds = SMOS_IC_Ds(os.path.join(testdata, 'L3_SMOS_IC', 'ASC'),
                        parameters=['Soil_Moisture'])
    else:
        ds = SMOS_L4_Ds(os.path.join(testdata, 'L4_SMOS_RZSM', 'SCIE'),
                        parameters=['RZSM'])
    image = ds.read(datetime(2018, 1, 1))
    assert np.isfinite(list(image.data.values())[0]).any()
    assert os.path.realpath(ds.fid.filename) not in _open_nc_files()

