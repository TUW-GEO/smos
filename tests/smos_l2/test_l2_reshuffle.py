import os
import pandas as pd
from tempfile import TemporaryDirectory
from smos.smos_l2.reshuffle import swath2ts, extend_ts, _default_variables
from smos.misc import read_summary_yml
from pynetcf.time_series import GriddedNcIndexedRaggedTs
from pygeogrids.netcdf import load_grid
import numpy as np

def test_reshuffle_and_update():
    img_path = os.path.join(os.path.join(os.path.dirname(__file__), '..', 'smos-test-data', 'L2_SMOS'))
    with TemporaryDirectory() as ts_path:
        swath2ts(img_path, ts_path, startdate='2022-01-01',  enddate='2022-01-02')  # enddate is excluded

        assert os.path.isfile(os.path.join(ts_path, 'grid.nc'))
        props = read_summary_yml(ts_path)
        assert pd.to_datetime(props['last_day']) == pd.to_datetime('2022-01-02')

        grid = load_grid(os.path.join(ts_path, 'grid.nc'))
        reader = GriddedNcIndexedRaggedTs(ts_path, grid=grid)

        ts = reader.read(74.958, 14.923)
        assert len(ts.index) == 1
        np.testing.assert_almost_equal(
            ts.loc['2022-01-01', 'Soil_Moisture'].values[0],
            0.236319, 5
        )

        ts = reader.read(-70.696, 50.629)
        assert len(ts) == 1

        reader.close()  # not great for production...

        extend_ts(img_path, ts_path)
        props = read_summary_yml(ts_path)
        assert pd.to_datetime(props['last_day']) == pd.to_datetime('2022-01-03')

        reader = GriddedNcIndexedRaggedTs(ts_path, grid=grid)

        ts = reader.read(-70.696, 50.629)
        np.testing.assert_almost_equal(
            ts.loc['2022-01-02', 'Soil_Moisture'].values[0],
            0.52442, 5
        )
        for var in _default_variables:
            assert var in ts.columns

        assert 'Overpass' in ts.columns

        assert 1 in ts.index.day
        assert 2 in ts.index.day
        assert 3 not in ts.index.day  # this must be excluded

        assert len(ts) == 2

        reader.close()
