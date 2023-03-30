from reporter.run_arv import run_arv as arv_main
from reporter.run_prv import run_prv as prv_main


def test_arv_flow(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "N")

    _file = "reporter/test/scenario_testing"

    arv_main("./reporter/test/stubs/config")
    prv_main("./reporter/test/stubs/config")
