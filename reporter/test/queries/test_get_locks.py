from reporter.queries import get_locks, get_arv_stakers
from reporter.config import load_conf


def test_get_locks():
    conf = load_conf("./reporter/test/stubs/config")

    stakers = get_arv_stakers(conf)
    addresses = [s.address for s in stakers]
    get_locks(addresses, conf)
