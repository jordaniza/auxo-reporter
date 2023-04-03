import pytest

from reporter.queries import get_locks, get_arv_stakers
from reporter.config import load_conf
from reporter.test.conftest import LIVE_CALLS_DISABLED, SKIP_REASON


@pytest.mark.skipif(LIVE_CALLS_DISABLED, reason=SKIP_REASON)
def test_get_locks():
    conf = load_conf("./reporter/test/stubs/config")

    stakers = get_arv_stakers(conf)
    addresses = [s.address for s in stakers]
    get_locks(addresses, conf)
