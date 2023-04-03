import pytest
from reporter.test.conftest import LIVE_CALLS_DISABLED, SKIP_REASON
from reporter import config
from reporter.run_arv import run_arv as arv_main
from reporter.run_prv import run_prv as prv_main


@pytest.mark.skipif(LIVE_CALLS_DISABLED, reason=SKIP_REASON)
def test_all(monkeypatch):

    monkeypatch.setattr(
        "builtins.input", lambda _: "./reporter/test/stubs/config/input.json"
    )

    epoch = config.main()
    monkeypatch.setattr("builtins.input", lambda _: "N")

    arv_main(epoch)
    prv_main(epoch)
