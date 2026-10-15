import os
import shutil
from datetime import datetime
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import mock

import pytest
from click.testing import CliRunner

from smos.smos_ic.download import SmosIcHttp
from smos.smos_ic.cli import cli_download, cli_update_img
from smos.misc import read_summary_yml

ROOT = '/cecsm/Land_products/L3_SMOS_IC_Soil_Moisture'
TEST_DATA = os.path.join(
    os.path.dirname(__file__), '..', 'smos-test-data', 'L3_SMOS_IC')


def _fake_server(listing):
    # Return a replacement for SmosIcHttp.exec that serves `cls` results
    # from the passed dict {subpath: [names]}
    def _exec(self, cmd):
        assert cmd.startswith('cls ')
        path = cmd[4:].rstrip('/')
        sub = path.replace(ROOT, '').strip('/')
        out = '\n'.join(f"{path}/{n}" for n in listing.get(sub, []))
        return SimpleNamespace(stdout=out.encode('utf-8'), returncode=0)

    return _exec


def _fn(orbit, d):
    return (f"SM_RE06_MIR_CDF3S{orbit[0]}_{d}T000000_{d}T235959"
            f"_106_001_8.DBL.nc")


LISTING = {
    '': ['ASC', 'DES', 'ReadMe.txt', 'documentation'],
    'ASC': ['2020', '2021'],
    'DES': ['2020', '2021'],
    'ASC/2021': [_fn('ASC', '20210101'),
                 _fn('ASC', '20210209')],
    'DES/2021': [_fn('DES', '20210101'),
                 _fn('DES', '20210208')],
    'ASC/2020': [_fn('ASC', '20201231')],
    'DES/2020': [_fn('DES', '20201230')],
}


def test_download_ic_sync_day():
    with TemporaryDirectory() as tempdir:
        http = SmosIcHttp(local_root=tempdir, skip_lftp_verify=True)
        cmds = http.sync(2018, 1, 1, opts='-e --testflag 1 2 3', dry_run=True)
        assert len(cmds) == 2
        for orbit, c in zip(['ASC', 'DES'], cmds):
            assert c == (f"mirror -c -e --testflag 1 2 3 "
                         f"--include-glob '*_20180101T000000_*' "
                         f"{ROOT}/{orbit}/2018 "
                         f"{os.path.join(tempdir, orbit, '2018')} --no-perms")


def test_download_ic_sync_month_and_year():
    with TemporaryDirectory() as tempdir:
        http = SmosIcHttp(
            local_root=tempdir, orbits='des', skip_lftp_verify=True)
        assert http.orbits == ['DES']
        c = http.sync(2018, 2, dry_run=True)
        assert c == [
            f"mirror -c --include-glob '*_201802??T000000_*' "
            f"{ROOT}/DES/2018 {os.path.join(tempdir, 'DES', '2018')}"
            f" --no-perms"
        ]
        c = http.sync(2018, dry_run=True)
        assert c == [
            f"mirror -c {ROOT}/DES/2018 "
            f"{os.path.join(tempdir, 'DES', '2018')} --no-perms"
        ]


def test_download_ic_invalid_input():
    with TemporaryDirectory() as tempdir:
        with pytest.raises(ValueError):
            SmosIcHttp(
                local_root=tempdir, orbits=['XYZ'], skip_lftp_verify=True)
        http = SmosIcHttp(local_root=tempdir, skip_lftp_verify=True)
        with pytest.raises(ValueError):
            http.sync(2009, 12, 31, dry_run=True)
        with pytest.raises(ValueError):
            http.sync(2018, day=1, dry_run=True)


def test_download_ic_period():
    with TemporaryDirectory() as tempdir:
        http = SmosIcHttp(
            local_root=tempdir, orbits=['ASC'], skip_lftp_verify=True)
        # 2010 is cut to the product start, 2011 is complete, in 2012
        # January is complete and February partial.
        cmds = http.sync_period('2009-06-01', '2012-02-02', dry_run=True)
        assert len(cmds) == 3

        globs_2010 = [g for g in cmds[0].split() if g.startswith("'*_2010")]
        assert globs_2010[0] == "'*_20100112T000000_*'"
        assert "'*_201002??T000000_*'" in globs_2010
        assert len(globs_2010) == 20 + 11

        assert cmds[1] == (f"mirror -c {ROOT}/ASC/2011 "
                           f"{os.path.join(tempdir, 'ASC', '2011')} "
                           f"--no-perms")
        assert cmds[2] == (f"mirror -c --include-glob '*_201201??T000000_*' "
                           f"--include-glob '*_20120201T000000_*' "
                           f"--include-glob '*_20120202T000000_*' "
                           f"{ROOT}/ASC/2012 "
                           f"{os.path.join(tempdir, 'ASC', '2012')} "
                           f"--no-perms")

        props = read_summary_yml(tempdir)
        assert props['first_day'] is None
        assert props['last_day'] is None
        assert props['last_update'] is not None


def test_overview_from_local_data():
    with TemporaryDirectory() as tempdir:
        for orbit in ['ASC', 'DES']:
            shutil.copytree(
                os.path.join(TEST_DATA, orbit), os.path.join(tempdir, orbit))
        http = SmosIcHttp(local_root=tempdir, skip_lftp_verify=True)
        http.write_overview()
        props = read_summary_yml(tempdir)
        assert props['first_day'] == '2018-01-01'
        # DES only has data for the first day
        assert props['last_day'] == '2018-01-01'

        http = SmosIcHttp(
            local_root=tempdir, orbits='ASC', skip_lftp_verify=True)
        http.write_overview()
        props = read_summary_yml(tempdir)
        assert props['last_day'] == '2018-01-03'


@mock.patch.object(SmosIcHttp, 'exec', _fake_server(LISTING))
def test_list_and_available_days():
    with TemporaryDirectory() as tempdir:
        http = SmosIcHttp(local_root=tempdir, skip_lftp_verify=True)
        assert http.list(filter='dir') == ['ASC', 'DES']
        assert http.list('ASC', filter='dir') == ['2020', '2021']
        assert http.list('ASC/2021', filter='dir') == []
        assert http.list('ASC/2021', filter='file') == LISTING['ASC/2021']

        assert http.last_available_day() == datetime(2021, 2, 8)
        http.orbits = ['ASC']
        assert http.last_available_day() == datetime(2021, 2, 9)

        http.orbits = ['ASC', 'DES']
        days = http.list_all_available_days(
            '2020-12-31', '2021-02-08', progressbar=False)
        assert days == [
            datetime(2020, 12, 31),
            datetime(2021, 1, 1),
            datetime(2021, 2, 8)
        ]


@mock.patch.object(SmosIcHttp, 'exec', _fake_server(LISTING))
@mock.patch.object(SmosIcHttp, 'verify_lftp_installed', lambda self: None)
def test_cli_download_and_update():
    with TemporaryDirectory() as tempdir:
        with mock.patch.object(SmosIcHttp, 'sync_period') as sp:
            r = CliRunner().invoke(cli_download,
                                   [tempdir, '-s', '2021-01-01', '-o', 'asc'])
            assert r.exit_code == 0, r.output
            kwargs = sp.call_args.kwargs
            assert kwargs['startdate'] == datetime(2021, 1, 1)
            assert kwargs['enddate'] == datetime(2021, 2, 9)

        # update requires an existing overview file
        r = CliRunner().invoke(cli_update_img, [tempdir])
        assert r.exit_code != 0

        os.makedirs(os.path.join(tempdir, 'ASC', '2021'))
        open(
            os.path.join(tempdir, 'ASC', '2021', _fn('ASC', '20210101')),
            'w').close()
        SmosIcHttp(tempdir, orbits='ASC').write_overview()

        with mock.patch.object(SmosIcHttp, 'sync_period') as sp:
            r = CliRunner().invoke(cli_update_img, [tempdir, '-o', 'ASC'])
            assert r.exit_code == 0, r.output
            kwargs = sp.call_args.kwargs
            assert kwargs['startdate'] == '2021-01-01'
            assert kwargs['enddate'] == datetime(2021, 2, 9)
