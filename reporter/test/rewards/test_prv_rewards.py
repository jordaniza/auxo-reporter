from decimal import Decimal, getcontext
import pytest

from reporter.models import (
    Config,
    Account,
    AccountState,
    TokenSummaryStats,
    RedistributionOption,
    PRV,
    RedistributionWeight,
    RedistributionContainer,
)
from reporter.rewards import prv_active_rewards, transfer_redistribution, redistribute

getcontext().prec = 42


@pytest.fixture
def token_summary_stats():
    # Create a sample TokenSummaryStats object
    return TokenSummaryStats(total=100, active=75, inactive=25)


# TODO 0 or 1?
@pytest.mark.parametrize("prv_reward_pc", [0.2, 0.25, 0.3, 0.5, 0.7])
def test_prv_active_rewards_active_and_inactive_rewards(
    token_summary_stats: TokenSummaryStats, config: Config, prv_reward_pc: float
):

    config.arv_percentage = 100 - int(prv_reward_pc * 100)
    active, inactive = prv_active_rewards(token_summary_stats, config)
    total_prv = Decimal(config.rewards.amount) * Decimal(prv_reward_pc)

    diff = Decimal(total_prv) - (active + inactive)
    assert abs(diff) < Decimal(100000)

    computed_active = (
        Decimal(token_summary_stats.active)
        * Decimal(total_prv)
        / Decimal(token_summary_stats.total)
    )

    computed_inactive = (
        Decimal(token_summary_stats.inactive)
        * Decimal(total_prv)
        / Decimal(token_summary_stats.total)
    )

    assert abs(active - computed_active) < Decimal(100000)
    assert abs(inactive - computed_inactive) < Decimal(100000)


def test_prv_active_rewards_no_supply(
    token_summary_stats: TokenSummaryStats, config: Config
):
    # Given
    token_summary_stats.total = "0"

    # When
    active_rewards, inactive_rewards = prv_active_rewards(token_summary_stats, config)

    # Then
    assert active_rewards == Decimal(0)
    assert inactive_rewards == Decimal(0)


def test_transfer_redistribution(config: Config, ADDRESSES):

    # Set up test data
    accounts = [
        Account(
            address=ADDRESSES[0],
            token=PRV(amount="0"),
            rewards=config.reward_token(amount="100"),
            state=AccountState.INACTIVE,
            notes=[],
        ),
        Account(
            address=ADDRESSES[1],
            token=PRV(amount="0"),
            rewards=config.reward_token(amount="200"),
            state=AccountState.INACTIVE,
            notes=[],
        ),
    ]

    # this should transfer to account 0
    r = RedistributionWeight(
        weight=40,
        rewards="75",
        address=ADDRESSES[0],
        option=RedistributionOption.TRANSFER,
    )

    # Call the function
    transfer_redistribution(accounts, r, config)

    # # Check that the rewards were redistributed correctly
    assert accounts[0].rewards.amount == "175"
    assert accounts[0].notes == ["Transfer of 75"]
    assert accounts[1].rewards.amount == "200"
    assert accounts[1].notes == []

    # Call the function again with a new account
    r = RedistributionWeight(
        address=ADDRESSES[2],
        rewards="75",
        weight=10,
        option=RedistributionOption.TRANSFER,
    )
    transfer_redistribution(accounts, r, config)

    # Check that the new account was added and rewards were set correctly
    assert len(accounts) == 3
    assert accounts[2].address == ADDRESSES[2]
    assert accounts[2].rewards.amount == "75"
    assert accounts[2].notes == ["Transfer of 75"]
    assert accounts[2].state == AccountState.INACTIVE


def test_redistribute(config: Config, ADDRESSES):
    conf = config
    # Set up test data
    accounts = [
        Account(
            address=ADDRESSES[0],
            token=PRV(amount="0"),
            rewards=conf.reward_token(amount="100"),
            state=AccountState.INACTIVE,
            notes=[],
        ),
        Account(
            address=ADDRESSES[1],
            token=PRV(amount="0"),
            rewards=conf.reward_token(amount="200"),
            state=AccountState.INACTIVE,
            notes=[],
        ),
    ]
    redistributions = [
        RedistributionWeight(
            address=ADDRESSES[0],
            rewards="50",
            option=RedistributionOption.TRANSFER,
            weight=1,
        ),
        RedistributionWeight(
            address=ADDRESSES[1],
            rewards="75",
            option=RedistributionOption.TRANSFER,
            weight=1,
        ),
        RedistributionWeight(
            address=ADDRESSES[2],
            rewards="25",
            option=RedistributionOption.TRANSFER,
            weight=1,
        ),
    ]
    container = RedistributionContainer(redistributions=redistributions)

    # Call the function
    updated_accounts = redistribute(accounts, container, conf)

    # Check that the rewards were redistributed correctly
    assert updated_accounts[0].rewards.amount == "150"
    assert updated_accounts[0].notes == ["Transfer of 50"]
    assert updated_accounts[1].rewards.amount == "275"
    assert updated_accounts[1].notes == ["Transfer of 75"]

    # Check that the manual transfer was processed correctly
    assert len(updated_accounts) == 3
    assert updated_accounts[2].address == ADDRESSES[2]
    assert updated_accounts[2].rewards.amount == "25"
    assert updated_accounts[2].notes == ["Transfer of 25"]
    assert updated_accounts[2].state == AccountState.INACTIVE
