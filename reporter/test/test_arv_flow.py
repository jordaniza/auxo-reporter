from reporter import config
from reporter.run_arv import run_arv as arv_main
from reporter.run_prv import run_prv as prv_main


def test_all(monkeypatch):

    monkeypatch.setattr(
        "builtins.input", lambda _: "./reporter/test/stubs/config/input.json"
    )

    epoch = config.main()
    monkeypatch.setattr("builtins.input", lambda _: "N")

    arv_main(epoch)
    prv_main(epoch)
