from reporter.models import Config
from reporter.writer import main


def test_write_claims(monkeypatch, config: Config):
    monkeypatch.setattr("reporter.writer.load_conf", lambda path: config)

    path = "reporter/test/stubs/db"
    main(path)
