import tempfile

import os
from smos.misc import get_first_last_day_images
import datetime

def test_first_last_date():
    rootf = os.path.join(os.path.join(os.path.dirname(__file__), 'smos-test-data'))

    with tempfile.TemporaryDirectory() as emptydir:
        s, e = get_first_last_day_images(emptydir)
        assert s is None
        assert e is None


    s, e = get_first_last_day_images(os.path.join(rootf, 'L2_SMOS'))
    assert s == datetime.date(2022,1,1)
    assert e == datetime.date(2022,1,3)

    s, e = get_first_last_day_images(os.path.join(rootf, 'L3_SMOS_IC', 'ASC'))
    assert s == datetime.date(2018,1,1)
    assert e == datetime.date(2018,1,3)

    s, e = get_first_last_day_images(os.path.join(rootf, 'L4_SMOS_RZSM', 'OPER'))
    assert s == datetime.date(2020,1,31)
    assert e == datetime.date(2020,1,31)