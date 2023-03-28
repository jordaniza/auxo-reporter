from reporter.ARV import main


def test_arv_flow(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "N")

    main("./reporter/test/stubs/config")
