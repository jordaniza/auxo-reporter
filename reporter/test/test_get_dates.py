import pytest
import datetime
from reporter.config import get_epoch_dates, EpochBoundary


def test_get_epoch_dates_valid():
    epoch = get_epoch_dates(3, 2023)
    assert isinstance(epoch, EpochBoundary)
    assert epoch.date == datetime.date(2023, 3, 1)
    assert epoch.start_date == datetime.datetime(
        2023, 3, 1, tzinfo=datetime.timezone.utc
    )
    assert epoch.end_date == datetime.datetime(
        2023, 3, 31, 23, 59, 59, tzinfo=datetime.timezone.utc
    )

    epoch = get_epoch_dates(12, 2023)
    assert isinstance(epoch, EpochBoundary)
    assert epoch.date == datetime.date(2023, 12, 1)
    assert epoch.start_date == datetime.datetime(
        2023, 12, 1, tzinfo=datetime.timezone.utc
    )
    assert epoch.end_date == datetime.datetime(
        2023, 12, 31, 23, 59, 59, tzinfo=datetime.timezone.utc
    )


def test_get_epoch_dates_invalid():
    with pytest.raises(ValueError):
        get_epoch_dates(0, 2023)
    with pytest.raises(ValueError):
        get_epoch_dates(13, 2023)
    with pytest.raises(ValueError):
        get_epoch_dates(2, 23)
    with pytest.raises(ValueError):
        get_epoch_dates(2, 2022)
