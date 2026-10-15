import os
import shutil
import pytest

from smos.smos_l3.download import extract_archives

L3_TEST_DATA = os.path.join(
    os.path.dirname(__file__), '..', 'smos-test-data', 'L3_SMOS')


@pytest.fixture(scope='session')
def l3_root(tmp_path_factory):
    """
    Copy of the L3 test data (as downloaded: .tgz archives in
    <product>/<YYYY>/<DOY|MM> folders) with all archives extracted.
    """
    root = tmp_path_factory.mktemp('l3') / 'L3_SMOS'
    shutil.copytree(L3_TEST_DATA, root)
    extract_archives(str(root))
    return str(root)
