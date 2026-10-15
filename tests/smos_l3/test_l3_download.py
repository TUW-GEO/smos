import os
import glob
import shutil
from datetime import datetime
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import mock

import pytest
from click.testing import CliRunner

from smos.smos_l3.download import (SmosL3Ftp, extract_archives, product_folder,
                                   local_campaigns)
from smos.smos_l3.cli import cli_download, cli_update_img
from smos.misc import read_summary_yml

ROOT = '/Land_products/GRIDDED/L3SM'
L3_TEST_DATA = os.path.join(
    os.path.dirname(__file__), '..', 'smos-test-data', 'L3_SMOS')


def _fake_server(listing):
    # Return a replacement for SmosL3Ftp.exec that serves `cls` results
    # from the passed dict {subpath: [names, folders end with /]}
    def _exec(self, cmd):
        assert cmd.startswith('cls -1 ')
        path = cmd[7:].rstrip('/')
        sub = path.replace(ROOT, '').strip('/')
        out = '\n'.join(f"{path}/{n}" for n in listing.get(sub, []))
        return SimpleNamespace(stdout=out.encode('utf-8'), returncode=0)

    return _exec


def _fn(campaign, product, d, version):
    return (f"SM_{campaign}_MIR_{product}_{d}T000000_{d}T235959_"
            f"{version}_001_7.tgz")


LISTING = {
    '': ['OPER/', 'RE07/', 'index.html', 'other/'],
    'RE07/MIR_CLF3SA': ['2020/', '2021/', 'index.html'],
    'OPER/MIR_CLF3SA': ['2021/', '2022/', 'index.html'],
    'RE07/MIR_CLF3SA/2021': ['156/', '157/', 'index.html'],
    'OPER/MIR_CLF3SA/2021': ['157/', '158/', '160/', 'index.html'],
    'OPER/MIR_CLF3SA/2022': ['001/', '002/', 'index.html'],
    'OPER/MIR_CLF3SA/2022/002': [
        _fn('OPER', 'CLF3SA', '20220102', 339), 'index.html'
    ],
    'OPER/MIR_CLF3SD': ['2022/'],
    'OPER/MIR_CLF3SD/2022': ['001/'],
    'OPER/MIR_CLF3SD/2022/001': [_fn('OPER', 'CLF3SD', '20220101', 339)],
    'OPER/MIR_CLF3DA': ['2025/'],
    'OPER/MIR_CLF3DA/2025': ['01/', '02/', '03/'],
}


def test_product_folder():
    assert product_folder('CLF3S', 'ASC') == 'MIR_CLF3SA'
    assert product_folder('mir_clf3m', 'des') == 'MIR_CLF3MD'
    with pytest.raises(ValueError):
        product_folder('CLF3X', 'ASC')
    with pytest.raises(ValueError):
        product_folder('CLF3S', 'XYZ')


def test_extract_archives():
    with TemporaryDirectory() as tempdir:
        shutil.copytree(
            os.path.join(L3_TEST_DATA, 'MIR_CLF3SA'),
            os.path.join(tempdir, 'MIR_CLF3SA'))
        extracted = extract_archives(tempdir)
        # 4 archives with a .DBL.nc and .HDR file each
        assert len(extracted) == 8
        assert sum(f.endswith('.DBL.nc') for f in extracted) == 4
        for f in extracted:
            assert os.path.isfile(f)
            assert os.path.dirname(f).endswith(('157', '158', '160'))
        # nothing to do if already extracted
        assert extract_archives(tempdir) == []
        assert len(extract_archives(tempdir, overwrite=True)) == 8


def test_extract_damaged_archive():
    # A damaged / incomplete archive (e.g. interrupted download) is skipped,
    # all other archives are extracted, no partial files are left
    with TemporaryDirectory() as tempdir:
        shutil.copytree(
            os.path.join(L3_TEST_DATA, 'MIR_CLF3SA'),
            os.path.join(tempdir, 'MIR_CLF3SA'))
        archives = sorted(
            glob.glob(os.path.join(tempdir, '**', '*.tgz'), recursive=True))
        damaged = archives[0]
        with open(damaged, 'rb') as fh:
            data = fh.read()
        with open(damaged, 'wb') as fh:
            fh.write(data[:len(data) // 2])
        with pytest.warns(UserWarning, match='damaged or incomplete'):
            extracted = extract_archives(tempdir)
        assert sum(f.endswith('.DBL.nc') for f in extracted) == 3
        assert not os.path.isfile(damaged.replace('.tgz', '.DBL.nc'))
        assert glob.glob(
            os.path.join(tempdir, '**', '*.part'), recursive=True) == []
        # once the archive is complete (next download), it is extracted
        with open(damaged, 'wb') as fh:
            fh.write(data)
        assert len(extract_archives(tempdir)) == 2


@mock.patch.object(SmosL3Ftp, 'exec', _fake_server(LISTING))
def test_list_and_last_day():
    with TemporaryDirectory() as tempdir:
        ftp = SmosL3Ftp(tempdir, skip_lftp_verify=True)
        # campaigns are read from the server, OPER last
        assert ftp.available_campaigns() == ['RE07', 'OPER']
        assert ftp.campaigns == ['RE07', 'OPER']
        assert ftp.list('RE07/MIR_CLF3SA') == ['2020', '2021']
        assert ftp.list('OPER/MIR_CLF3SA/2022/002', filter='dir') == []
        assert ftp.list('OPER/MIR_CLF3SA/2022/002', filter='file') == \
            [_fn('OPER', 'CLF3SA', '20220102', 339)]
        # last day available for both orbits
        assert ftp.last_available_day() == datetime(2022, 1, 1)
        ftp.folders = ['MIR_CLF3SA']
        assert ftp.last_available_day() == datetime(2022, 1, 2)
        # no files of a campaign on the server
        ftp.campaigns = ['RE07']
        with pytest.raises(ValueError, match='No MIR_CLF3SA data'):
            ftp.last_available_day()


def test_new_campaign_on_server():
    # A new reprocessing (RE08) is found and handled like RE07
    listing = {
        **LISTING, '': ['OPER/', 'RE07/', 'RE08/', 'RE10/'],
        'RE08/MIR_CLF3SA': ['2010/', '2022/'],
        'RE08/MIR_CLF3SA/2022': ['001/', '003/'],
        'RE08/MIR_CLF3SA/2022/003': [_fn('RE08', 'CLF3SA', '20220103', 400)]
    }
    with TemporaryDirectory() as tempdir, \
            mock.patch.object(SmosL3Ftp, 'exec', _fake_server(listing)):
        ftp = SmosL3Ftp(tempdir, orbits='ASC', skip_lftp_verify=True)
        assert ftp.campaigns == ['RE07', 'RE08', 'RE10', 'OPER']
        # latest file over all campaigns
        assert ftp.last_available_day() == datetime(2022, 1, 3)
        cmds = ftp.sync_period('2022-01-01', '2022-01-03', dry_run=True)
        assert [c.split(' ')[-3] for c in cmds] == [
            f"{ROOT}/RE08/MIR_CLF3SA/2022/001",
            f"{ROOT}/RE08/MIR_CLF3SA/2022/003",
            f"{ROOT}/OPER/MIR_CLF3SA/2022/001",
            f"{ROOT}/OPER/MIR_CLF3SA/2022/002"
        ]
        # campaigns can also be passed (in any order)
        ftp = SmosL3Ftp(
            tempdir, campaigns=['oper', 'RE08'], skip_lftp_verify=True)
        assert ftp.campaigns == ['RE08', 'OPER']


@mock.patch.object(SmosL3Ftp, 'exec', _fake_server(LISTING))
def test_sync_period_daily_product():
    with TemporaryDirectory() as tempdir:
        ftp = SmosL3Ftp(tempdir, orbits='ASC', skip_lftp_verify=True)
        assert ftp.folders == ['MIR_CLF3SA']
        cmds = ftp.sync_period('2021-06-05', '2021-06-09', dry_run=True)

        def cmd(campaign, sub):
            return (f"mirror -c --include-glob '*.tgz' "
                    f"{ROOT}/{campaign}/MIR_CLF3SA/2021/{sub} "
                    f"{os.path.join(tempdir, 'MIR_CLF3SA', '2021', sub)} "
                    f"--no-perms")

        # only day folders that exist on the server are mirrored, files of
        # both campaigns are stored in the same local folder
        assert cmds == [
            cmd('RE07', '156'),
            cmd('RE07', '157'),
            cmd('OPER', '157'),
            cmd('OPER', '158'),
            cmd('OPER', '160')
        ]

        # a complete year is synced with one command, years that are not
        # on the server are skipped
        ftp.campaigns = ['RE07']
        cmds = ftp.sync_period('2019-06-01', '2020-12-31', dry_run=True)
        assert cmds == [
            f"mirror -c --include-glob '*.tgz' "
            f"{ROOT}/RE07/MIR_CLF3SA/2020 "
            f"{os.path.join(tempdir, 'MIR_CLF3SA', '2020')} "
            f"--no-perms"
        ]
        # no download, no overview file for a dry run
        assert not os.path.isfile(
            os.path.join(tempdir, 'MIR_CLF3SA', 'overview.yml'))


@mock.patch.object(SmosL3Ftp, 'exec', _fake_server(LISTING))
def test_sync_period_monthly_folders():
    with TemporaryDirectory() as tempdir:
        ftp = SmosL3Ftp(
            tempdir,
            product='CLF3D',
            orbits=['ASC'],
            campaigns='OPER',
            skip_lftp_verify=True)
        cmds = ftp.sync_period(
            '2025-01-30', '2025-02-28', opts='--parallel=2', dry_run=True)
        assert cmds == [
            f"mirror -c --parallel=2 --include-glob '*_20250130T000000_*.tgz' "
            f"--include-glob '*_20250131T000000_*.tgz' "
            f"{ROOT}/OPER/MIR_CLF3DA/2025/01 "
            f"{os.path.join(tempdir, 'MIR_CLF3DA', '2025', '01')} --no-perms",
            f"mirror -c --parallel=2 --include-glob '*.tgz' "
            f"{ROOT}/OPER/MIR_CLF3DA/2025/02 "
            f"{os.path.join(tempdir, 'MIR_CLF3DA', '2025', '02')} --no-perms",
        ]


def test_invalid_input():
    with TemporaryDirectory() as tempdir:
        with pytest.raises(ValueError):
            SmosL3Ftp(tempdir, product='XYZ', skip_lftp_verify=True)
        with pytest.raises(ValueError):
            SmosL3Ftp(tempdir, campaigns=['XYZ'], skip_lftp_verify=True)
        with pytest.raises(ValueError):
            SmosL3Ftp(tempdir, campaigns='RE', skip_lftp_verify=True)


def test_sync_extracts_and_writes_overview():
    # Simulate a download by copying the test archives in exec
    def _exec(self, cmd):
        if cmd.startswith('cls -1 '):
            return _fake_server({
                '': ['RE07/', 'OPER/'],
                'RE07/MIR_CLF3SA': ['2021/'],
                'OPER/MIR_CLF3SA': ['2021/'],
                'RE07/MIR_CLF3SA/2021': ['157/'],
                'OPER/MIR_CLF3SA/2021': ['157/', '158/', '160/']
            })(self, cmd)
        for c in cmd.split(' && '):
            src_sub, target = c.split(' ')[-3:-1]
            sub = src_sub.split('MIR_CLF3SA/')[1]
            campaign = src_sub.split('/')[4]
            src = os.path.join(L3_TEST_DATA, 'MIR_CLF3SA', *sub.split('/'))
            os.makedirs(target, exist_ok=True)
            for f in os.listdir(src):
                if f.startswith(f"SM_{campaign}"):
                    shutil.copy(os.path.join(src, f), target)
        return SimpleNamespace(stdout=b'', stderr=b'', returncode=0)

    with TemporaryDirectory() as tempdir:
        with mock.patch.object(SmosL3Ftp, 'exec', _exec):
            ftp = SmosL3Ftp(tempdir, orbits='ASC', skip_lftp_verify=True)
            r = ftp.sync_period('2021-06-06', '2021-06-10')
        # one session per campaign and year
        assert len(r) == 2
        folder = os.path.join(tempdir, 'MIR_CLF3SA', '2021')
        assert sorted(os.listdir(os.path.join(folder, '157'))) == sorted([
            f"SM_{c}_MIR_CLF3SA_20210606T000000_20210606T235959_{v}_001_7.{e}"
            for c, v in [('RE07', 338), ('OPER', 339)]
            for e in ('tgz', 'DBL.nc', 'HDR')
        ])
        props = read_summary_yml(os.path.join(tempdir, 'MIR_CLF3SA'))
        assert props['first_day'] == '2021-06-06'
        assert props['last_day'] == '2021-06-09'
        assert props['campaigns'] == ['RE07', 'OPER']
        assert local_campaigns(folder) == ['RE07', 'OPER']


@mock.patch.object(SmosL3Ftp, 'verify_lftp_installed', lambda self: None)
def test_cli_download_and_update():
    with TemporaryDirectory() as tempdir:
        with mock.patch.object(SmosL3Ftp, 'sync_period') as sp, \
                mock.patch.object(SmosL3Ftp, 'last_available_day',
                                  return_value=datetime(2026, 1, 1)):
            r = CliRunner().invoke(cli_download, [
                tempdir, '-p', 'clf3m', '-s', '2021-01-01', '-o', 'asc', '-c',
                'oper'
            ])
            assert r.exit_code == 0, r.output
            assert sp.call_args.kwargs['startdate'] == datetime(2021, 1, 1)
            assert sp.call_args.kwargs['enddate'] == datetime(2026, 1, 1)

        # update requires an existing record
        r = CliRunner().invoke(cli_update_img, [tempdir, '-o', 'ASC'])
        assert r.exit_code != 0

        shutil.copytree(
            os.path.join(L3_TEST_DATA, 'MIR_CLF3SA'),
            os.path.join(tempdir, 'MIR_CLF3SA'))
        SmosL3Ftp(
            tempdir, orbits='ASC', skip_lftp_verify=True).write_overview()

        def update(server_campaigns):
            calls = []

            def sync_period(self, startdate, enddate):
                calls.append((list(self.campaigns), startdate, enddate))

            with mock.patch.object(SmosL3Ftp, 'sync_period', sync_period), \
                    mock.patch.object(SmosL3Ftp, 'available_campaigns',
                                      return_value=server_campaigns), \
                    mock.patch.object(SmosL3Ftp, 'last_available_day',
                                      return_value=datetime(2026, 1, 1)):
                r = CliRunner().invoke(cli_update_img, [tempdir, '-o', 'ASC'])
            assert r.exit_code == 0, r.output
            return calls, r.output

        # the local test data contains RE07 and OPER files: update from the
        # last local day
        calls, _ = update(['RE07', 'OPER'])
        assert calls == [(['RE07', 'OPER'], '2021-06-09', datetime(2026, 1,
                                                                   1))]

        # a new reprocessing is downloaded for the whole local period
        calls, out = update(['RE07', 'RE08', 'OPER'])
        assert calls == [(['RE07', 'OPER'], '2021-06-09', datetime(2026, 1,
                                                                   1)),
                         (['RE08'], '2021-06-06', datetime(2026, 1, 1))]
        assert 'RE08' in out

        # overview files of older versions don't list the campaigns
        yml = os.path.join(tempdir, 'MIR_CLF3SA', 'overview.yml')
        with open(yml) as f:
            lines = [
                line for line in f if not line.startswith('campaigns') and
                not line.startswith('- ')
            ]
        with open(yml, 'w') as f:
            f.writelines(lines)
        calls, _ = update(['RE07', 'OPER'])
        assert calls == [(['RE07', 'OPER'], '2021-06-09', datetime(2026, 1,
                                                                   1))]
