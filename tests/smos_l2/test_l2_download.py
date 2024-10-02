from tempfile import TemporaryDirectory
from smos.smos_l2.download import SmosDissEoFtp
def test_download_l2():
    with TemporaryDirectory() as tempdir:
        ftp = SmosDissEoFtp(local_root=tempdir, username='asd', password='asd',
                            skip_lftp_verify=True)
        c = ftp.sync(2022, 1, 1, opts='-e --testflag 1 2 3', dry_run=True)
        assert c == f'mirror -c -e --testflag 1 2 3 /SMOS/L2SM/MIR_SMUDP2_nc/2022/01/01 {tempdir}/2022/01/01 −−no−perms'

def test_download_l2_period():
    with TemporaryDirectory() as tempdir:
        ftp = SmosDissEoFtp(local_root=tempdir, username='asd', password='asd',
                            skip_lftp_verify=True)
        cmds = ftp.sync_period('2022-01-01', '2022-01-03', dry_run=True)

        for d in [1, 2, 3]:
            assert cmds[d-1] == f'mirror -c /SMOS/L2SM/MIR_SMUDP2_nc/2022/01/0{d} {tempdir}/2022/01/0{d} −−no−perms'