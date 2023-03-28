import pytest
from pydantic import ValidationError
from reporter.config import create_conf, main, load_conf, get_epoch_dates
import datetime

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


def test_get_dates():
    # Test case 1: January 2023
    month = 1
    year = 2023
    expected_output = (
        datetime.date(2023, 1, 1),
        datetime.datetime(2023, 1, 1, 0, 0, 0),
        datetime.datetime(2023, 1, 31, 23, 59, 59),
    )
    assert get_epoch_dates(month, year) == expected_output

    # Test case 2: February 2024 (leap year)
    month = 2
    year = 2024
    expected_output = (
        datetime.date(2024, 2, 1),
        datetime.datetime(2024, 2, 1, 0, 0, 0),
        datetime.datetime(2024, 2, 29, 23, 59, 59),
    )
    assert get_epoch_dates(month, year) == expected_output

    # Test case 3: Invalid month
    month = 13
    year = 2023
    with pytest.raises(ValueError):
        get_epoch_dates(month, year)

    # Test case 4: Invalid year
    month = 5
    year = -1
    with pytest.raises(ValueError):
        get_epoch_dates(month, year)
