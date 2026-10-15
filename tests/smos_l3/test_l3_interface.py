import os
import glob
from datetime import datetime

import numpy as np
import numpy.testing as nptest
import pytest
from netCDF4 import Dataset

from smos.grid import EASE25CellGrid
from smos.smos_l3.interface_l3 import SMOS_L3_Img, SMOS_L3_Ds

# product folder, image date, number of variables, a variable to check
PRODUCTS = [
    ('MIR_CLF3SA', datetime(2021, 6, 6), 15, 'Soil_Moisture'),
    ('MIR_CLF31A', datetime(2025, 1, 1), 52, 'Soil_Moisture'),
    ('MIR_CLF33A', datetime(2025, 1, 1), 15, 'Soil_Moisture'),
    ('MIR_CLF3EA', datetime(2025, 1, 1), 12, 'Dielect_Const_Module'),
    ('MIR_CLF3DA', datetime(2025, 1, 1), 44, 'Soil_Moisture_med'),
    ('MIR_CLF3MA', datetime(2025, 1, 1), 15, 'Soil_Moisture'),
]


def _raw(filename, var, idx=None):
    # Read a variable from the netcdf file directly, north up (as returned
    # by the reader, the files are stored south up)
    with Dataset(filename) as ds:
        data = ds[var][:] if idx is None else ds[var][:, :, idx]
    return np.flipud(np.ma.filled(data.astype(float), np.nan))


@pytest.mark.parametrize("folder,date,n_vars,var", PRODUCTS)
def test_read_all_products(l3_root, folder, date, n_vars, var):
    ds = SMOS_L3_Ds(os.path.join(l3_root, folder))
    image = ds.read(date)
    assert len(image.data) == n_vars
    assert image.data[var].shape == (584, 1388)
    assert image.timestamp == date

    # the image values are the same as in the netcdf file
    base, idx = var, None
    if var.endswith('_med'):
        base, idx = var[:-4], 0
    raw = _raw(ds.fid.filename, base, idx)
    assert np.isfinite(raw).sum() > 10000
    nptest.assert_array_equal(np.isnan(image.data[var]), np.isnan(raw))
    nptest.assert_allclose(image.data[var], raw)

    # coordinates
    assert image.lat[0, 0] > 83 and image.lat[-1, 0] < -83
    assert image.lon[0, 0] < -179 and image.lon[0, -1] > 179
    # packing attributes are removed, data is already unpacked
    assert 'scale_factor' not in image.metadata[var]


def test_split_third_dimension(l3_root):
    ds = SMOS_L3_Ds(
        os.path.join(l3_root, 'MIR_CLF3DA'),
        parameters=['Soil_Moisture', 'Science_Flags_max'])
    image = ds.read(datetime(2025, 1, 1))
    assert list(image.data.keys()) == [
        'Soil_Moisture_med', 'Soil_Moisture_min', 'Soil_Moisture_max',
        'Science_Flags_max'
    ]
    sm_min, sm_max = image.data['Soil_Moisture_min'], image.data[
        'Soil_Moisture_max']
    valid = np.isfinite(sm_min) & np.isfinite(sm_max)
    assert np.all(sm_min[valid] <= image.data['Soil_Moisture_med'][valid])
    assert np.all(image.data['Soil_Moisture_med'][valid] <= sm_max[valid])
    assert '(max)' in image.metadata['Soil_Moisture_max']['long_name']

    ds = SMOS_L3_Ds(
        os.path.join(l3_root, 'MIR_CLF31A'), parameters=['Dielect_Const'])
    image = ds.read(datetime(2025, 1, 1))
    assert list(image.data.keys()) == ['Dielect_Const_re', 'Dielect_Const_im']


def test_campaign_and_version_selection(l3_root):
    # 2021-06-06: RE07 (v338) and OPER (v339) file are available
    path = os.path.join(l3_root, 'MIR_CLF3SA')
    ds = SMOS_L3_Ds(path, parameters='Soil_Moisture')
    ds.read(datetime(2021, 6, 6))
    assert os.path.basename(ds.fid.filename).startswith('SM_OPER_')

    ds = SMOS_L3_Ds(path, parameters='Soil_Moisture', version=338)
    image = ds.read(datetime(2021, 6, 6))
    assert os.path.basename(ds.fid.filename).startswith('SM_RE07_')
    assert np.isfinite(image.data['Soil_Moisture']).any()
    # no v338 for a date only covered by OPER
    image = ds.read(datetime(2021, 6, 7))
    assert image.metadata['Soil_Moisture']['image_missing'] == 1


def test_missing_image_and_subset(l3_root):
    subgrid = EASE25CellGrid(bbox=(-11., 34., 43., 71.))
    ds = SMOS_L3_Ds(
        os.path.join(l3_root, 'MIR_CLF3SA'),
        parameters=['Soil_Moisture', 'Science_Flags'],
        grid=subgrid)
    image = ds.read(datetime(2021, 6, 8))  # no file
    assert image.metadata['Soil_Moisture']['image_missing'] == 1
    assert np.all(np.isnan(image.data['Soil_Moisture']))
    # empty images have the same data types as the actual images
    assert np.issubdtype(image.data['Science_Flags'].dtype, np.integer)
    assert np.all(np.ma.getmaskarray(image.data['Science_Flags']))
    assert image.data['Science_Flags'].fill_value == -1

    image = ds.read(datetime(2021, 6, 7))
    assert image.data['Soil_Moisture'].shape == (113, 208)
    assert image.metadata['Soil_Moisture']['image_missing'] == 0
    # integer flags keep their (masked) fill values
    flags = image.data['Science_Flags']
    assert np.issubdtype(flags.dtype, np.integer)
    assert np.ma.is_masked(flags)


def test_flatten(l3_root):
    fname = glob.glob(
        os.path.join(l3_root, 'MIR_CLF3SD', '2021', '157', '*.DBL.nc'))[0]
    image = SMOS_L3_Img(fname, parameters=['Soil_Moisture'], flatten=True)\
        .read(datetime(2021, 6, 6))
    assert image.data['Soil_Moisture'].shape == (584 * 1388,)
    raw = np.flipud(_raw(fname, 'Soil_Moisture'))  # south up, as the grid
    nptest.assert_allclose(image.data['Soil_Moisture'], raw.flatten())


def test_errors(l3_root):
    with pytest.raises(ValueError, match='derive product'):
        SMOS_L3_Ds(l3_root)
    with pytest.raises(ValueError, match='Unknown product'):
        SMOS_L3_Ds(l3_root, product='CLF3X', orbit='A')
    ds = SMOS_L3_Ds(
        os.path.join(l3_root, 'MIR_CLF3EA'), parameters=['Soil_Moisture'])
    with pytest.raises(ValueError, match='Soil_Moisture'):
        ds.read(datetime(2025, 1, 1))


@pytest.mark.parametrize("folder,expected", [
    ('MIR_CLF3SA',
     [datetime(2025, 1, d) for d in range(1, 32)] + [datetime(2025, 2, 1)]),
    ('MIR_CLF33A',
     [datetime(2025, 1, d) for d in range(1, 32)] + [datetime(2025, 2, 1)]),
    ('MIR_CLF3DA', [
        datetime(2025, 1, 1),
        datetime(2025, 1, 11),
        datetime(2025, 1, 21),
        datetime(2025, 2, 1)
    ]),
    ('MIR_CLF3MA', [datetime(2025, 1, 1),
                    datetime(2025, 2, 1)]),
])
def test_tstamps_for_daterange(l3_root, folder, expected):
    ds = SMOS_L3_Ds(os.path.join(l3_root, folder))
    assert ds.tstamps_for_daterange(
        datetime(2025, 1, 1), datetime(2025, 2, 1, 12)) == expected
