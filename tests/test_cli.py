import os
import glob
import tempfile

import numpy as np
import numpy.testing as nptest
import pytest
from click.testing import CliRunner

from smos.cli import smos
from smos.interface import SMOSTs
from smos.smos_ic.reshuffle_ic import main

TESTDATA = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "smos-test-data")


@pytest.mark.parametrize("group,commands", [
    ('l2', ['download', 'update_img', 'reshuffle', 'update_ts']),
    ('ic', ['download', 'update_img', 'reshuffle']),
    ('l3', ['download', 'update_img', 'reshuffle', 'update_ts']),
    ('l4', ['reshuffle']),
])
def test_command_groups(group, commands):
    r = CliRunner().invoke(smos, [group, '--help'])
    assert r.exit_code == 0, r.output
    for c in commands:
        assert c in r.output
        rc = CliRunner().invoke(smos, [group, c, '--help'])
        assert rc.exit_code == 0, rc.output


def test_ic_reshuffle():
    img_path = os.path.join(TESTDATA, "L3_SMOS_IC", "ASC")
    args = [
        '-v', 'Soil_Moisture,Scene_Flags', '--bbox', '-11', '34', '43', '71',
        '--only_land'
    ]
    with tempfile.TemporaryDirectory() as ts_path:
        # start and end date from the available images (2018-01-01 to 03)
        r = CliRunner().invoke(smos,
                               ['ic', 'reshuffle', img_path, ts_path] + args)
        assert r.exit_code == 0, r.output
        assert len(glob.glob(os.path.join(ts_path, "*.nc"))) == 79
        ds = SMOSTs(
            ts_path, ioclass_kws={'read_bulk': True}, drop_missing=False)
        ts = ds.read(20.36023, 47.682177)
        ds.close()
        assert list(ts.columns) == ['Soil_Moisture', 'Scene_Flags']
        assert len(ts.index) == 3  # 2018-01-02 is missing, filled with NaN
        assert np.isfinite(ts['Soil_Moisture'].iloc[0])
        assert np.isnan(ts['Soil_Moisture'].iloc[1])

        # same as with the python function
        with tempfile.TemporaryDirectory() as ts_path_main:
            main([
                img_path, ts_path_main, '2018-01-01', '2018-01-03',
                '--parameters', 'Soil_Moisture', 'Scene_Flags', '--bbox',
                '-11', '34', '43', '71', '--only_land', 'True'
            ])
            ds = SMOSTs(
                ts_path_main,
                ioclass_kws={'read_bulk': True},
                drop_missing=False)
            assert ts.equals(ds.read(20.36023, 47.682177))
            ds.close()


def test_l4_reshuffle():
    img_path = os.path.join(TESTDATA, "L4_SMOS_RZSM", "SCIE")
    with tempfile.TemporaryDirectory() as ts_path:
        r = CliRunner().invoke(smos, [
            'l4', 'reshuffle', img_path, ts_path, '-s', '2018-01-01', '-e',
            '2018-01-03', '-v', 'RZSM,QUAL'
        ])
        assert r.exit_code == 0, r.output
        assert len(glob.glob(os.path.join(ts_path, "*.nc"))) == 2449
        ds = SMOSTs(
            ts_path, ioclass_kws={'read_bulk': True}, drop_missing=False)
        ts = ds.read(150.625, -32.125)  # same point as in test_L4reshuffle
        nptest.assert_allclose(ts['RZSM'].values,
                               np.array([0.136741, 0.136160, np.nan]), 4)
        ds.close()
