import pytest
from pydantic import ValidationError
from reporter.config import create_conf, main, load_conf

PATH = "reporter/test/stubs/config/"


def test_config_file(monkeypatch):

    conf = create_conf(f"{PATH}/input.json")
    monkeypatch.setattr("builtins.input", lambda _: f"{PATH}/input.json")
    main()

    epoch_conf = load_conf(PATH)
    assert epoch_conf.block_snapshot == conf.block_snapshot
    assert epoch_conf.distribution_window == conf.distribution_window
    assert epoch_conf.rewards == conf.rewards

    assert epoch_conf.date == f"{conf.year}-{conf.month}"


@pytest.mark.parametrize(
    "invalids", [f"reporter/test/stubs/config/invalid_{i}.json" for i in range(1, 4)]
)
def test_invalid_json_fails(invalids):
    with pytest.raises(ValidationError):
        create_conf(invalids)
