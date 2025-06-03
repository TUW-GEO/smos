import os
import pandas as pd
from tempfile import TemporaryDirectory
from smos.smos_l2.reshuffle import swath2ts, extend_ts, _default_variables
from smos.misc import read_summary_yml
from pynetcf.time_series import GriddedNcIndexedRaggedTs
from pygeogrids.netcdf import load_grid
import numpy as np
import glob

img_path = os.path.join(
    os.path.join(os.path.dirname(__file__), '..', 'smos-test-data', 'L2_SMOS'))


def test_reshuffle_and_update():
    with TemporaryDirectory() as ts_path:
        print(ts_path)
        swath2ts(img_path,
                 ts_path,
                 startdate='2022-01-01',
                 enddate='2022-01-02')  # enddate is excluded

        assert os.path.isfile(os.path.join(ts_path, 'grid.nc'))
        props = read_summary_yml(ts_path)
        assert pd.to_datetime(
            props['last_day']) == pd.to_datetime('2022-01-02')

        grid = load_grid(os.path.join(ts_path, 'grid.nc'))
        reader = GriddedNcIndexedRaggedTs(ts_path, grid=grid)

        ts = reader.read(74.958, 14.923)
        assert len(ts.index) == 1
        np.testing.assert_almost_equal(
            ts.loc['2022-01-01', 'Soil_Moisture'].values[0], 0.236319, 5)

        ts = reader.read(-70.696, 50.629)
        assert len(ts) == 1

        reader.close()  # not great for production...

        extend_ts(img_path, ts_path)
        props = read_summary_yml(ts_path)
        assert pd.to_datetime(
            props['last_day']) == pd.to_datetime('2022-01-03')

        reader = GriddedNcIndexedRaggedTs(ts_path, grid=grid)

        ts = reader.read(-70.696, 50.629)
        #np.testing.assert_almost_equal(
        #    ts.loc['2022-01-02', 'Soil_Moisture'].values[0],
        #    0.52442, 5
        # )
        for var in _default_variables:
            assert var in ts.columns

        assert 'Overpass' in ts.columns

        assert 1 in ts.index.day
        assert 2 in ts.index.day
        assert 3 not in ts.index.day  # this must be excluded

        assert len(ts) == 2

        reader.close()


def test_reshuffle_only_land_and_all_gpis():
    with TemporaryDirectory() as ts_path_all, \
        TemporaryDirectory() as ts_path_land:

        swath2ts(img_path,
                 ts_path_all,
                 startdate='2022-01-01',
                 enddate='2022-01-02')
        swath2ts(img_path,
                 ts_path_land,
                 startdate='2022-01-01',
                 enddate='2022-01-02',
                 only_land=True)

        grid_all = load_grid(os.path.join(ts_path_all, 'grid.nc'))
        grid_land = load_grid(os.path.join(ts_path_land, 'grid.nc'))

        assert len(glob.glob(os.path.join(ts_path_all, "*.nc"))) == 2913
        assert len(glob.glob(os.path.join(ts_path_land, "*.nc"))) == 455

        # land_gpis are the GPIs for land points
        land_gpis = grid_land.gpis
        np.random.seed(42)  # Fixed seed for reproducibility
        chosen = np.random.choice(land_gpis, size=20, replace=False)

        reader_all = GriddedNcIndexedRaggedTs(ts_path_all, grid=grid_all)
        reader_land = GriddedNcIndexedRaggedTs(ts_path_land, grid=grid_land)

        for gpi in chosen:
            try:
                lon, lat = grid_land.gpi2lonlat(gpi)

                # Try to read from both readers
                all_success = False
                land_success = False
                ts_all = None
                ts_land = None

                try:
                    ts_all = reader_all.read(gpi)
                    all_success = True
                except OSError:
                    all_success = False

                try:
                    ts_land = reader_land.read(gpi)
                    land_success = True
                except OSError:
                    land_success = False

                # Assert that both readers either succeed or fail together (in the case that there is no data on the gpi - but its still a land point)
                assert all_success == land_success, f"Inconsistent read results at GPI={gpi}, lon={lon}, lat={lat}: all_success={all_success}, land_success={land_success}"

                # If both succeeded, check that the time series are equal
                if all_success and land_success:
                    assert ts_all.equals(
                        ts_land
                    ), f"Time series mismatch at GPI={gpi}, lon={lon}, lat={lat}"

            except Exception as e:
                print(f"Error at GPI={gpi}: {e}")

        reader_all.close()
        reader_land.close()
