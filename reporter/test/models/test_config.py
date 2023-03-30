import pytest
from datetime import datetime
from decimal import Decimal
from reporter.models import (
    InputConfig,
    RedistributionWeight,
    RedistributionOption,
    Config,
    BadConfigException,
)


@pytest.fixture
def input_config() -> InputConfig:
    return InputConfig(
        year=2023,
        month=1,
        block_snapshot=100000,
        distribution_window=1,
        rewards={
            "address": "0x1234567890123456789012345678901234567890",
            "amount": "1000",
            "decimals": 18,
            "symbol": "RWD",
        },
        redistributions=[
            RedistributionWeight(
                address="0x1", weight=1, option=RedistributionOption.TRANSFER
            ),
            RedistributionWeight(
                address="0x2", weight=2, option=RedistributionOption.TRANSFER
            ),
        ],
        arv_percentage=0.7,
    )


@pytest.mark.parametrize("pc", [-0.01, 1.01])
def test_validate_arv_percentage(input_config: InputConfig, pc):
    dct = input_config.dict()

    with pytest.raises(BadConfigException, match="ARV percentage out of range"):
        dct["arv_percentage"] = pc
        InputConfig(**dct)


@pytest.mark.parametrize("month", [0, 13])
def test_validate_month(input_config: InputConfig, month):
    dct = input_config.dict()

    with pytest.raises(BadConfigException, match="Month out of range"):
        dct["month"] = month
        InputConfig(**dct)


@pytest.mark.parametrize("year", [0, 13])
def test_validate_year(input_config: InputConfig, year):
    dct = input_config.dict()

    with pytest.raises(BadConfigException, match="Year is likely incorrect"):
        dct["year"] = year
        InputConfig(**dct)


@pytest.mark.parametrize(
    "r",
    [
        RedistributionWeight(
            address="0x1", weight=3, option=RedistributionOption.TRANSFER
        ),
    ],
)
def test_validate_redistributions_duplicate(input_config: InputConfig, r):
    dct = input_config.dict()

    with pytest.raises(BadConfigException, match="Passed Duplicate Transfer Addresses"):
        dct["redistributions"].append(r.dict())
        InputConfig(**dct)


def test_validate_redistributions_ensure(input_config: InputConfig):
    dct = input_config.dict()

    with pytest.raises(
        BadConfigException,
        match="Must provide a transfer address if not redistributing to stakers",
    ):
        RedistributionWeight(weight=3, option=RedistributionOption.TRANSFER)

    with pytest.raises(
        BadConfigException,
        match="Cannot pass an address if redistributing",
    ):
        RedistributionWeight(
            address="0x8", weight=3, option=RedistributionOption.REDISTRIBUTE_PRV
        )


@pytest.fixture
def config(input_config: InputConfig) -> Config:
    start_date = datetime(year=input_config.year, month=input_config.month, day=1)
    end_date = (
        start_date.replace(
            month=start_date.month % 12 + 1,
            year=start_date.year + start_date.month // 12,
        )
    ).replace(day=1, microsecond=0, second=0, minute=0)
    return Config(
        year=input_config.year,
        month=input_config.month,
        block_snapshot=input_config.block_snapshot,
        distribution_window=input_config.distribution_window,
        rewards=input_config.rewards,
        redistributions=input_config.redistributions,
        arv_percentage=input_config.arv_percentage,
        date=start_date.strftime("%Y-%m"),
        start_timestamp=int(start_date.timestamp()),
        end_timestamp=int((end_date.timestamp() - 1)),
    )


@pytest.mark.parametrize("split", [0.5, 0.6, 0.75, 0.8, 0.9, 1])
def test_conf_reward_split(config: Config, split):
    dct = config.dict()

    dct["arv_percentage"] = split

    config = Config(**dct)

    assert round(config.arv_rewards) == 1000 * split
