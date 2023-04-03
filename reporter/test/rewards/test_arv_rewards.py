from decimal import Decimal
from reporter import utils
from reporter.models import (
    Account,
    AccountState,
    Config,
    ARVStaker,
    TokenSummaryStats,
    ERC20Amount,
    ARVRewardSummary,
    ARV,
)
from reporter.rewards import (
    compute_rewards,
    init_account_rewards,
    tokens_by_status,
    compute_token_stats,
    distribute,
)


def test_init_account_rewards(ADDRESSES, config):
    stakers = [
        ARVStaker(
            address=ADDRESSES[0],
            arv_holding="100",
            rewards="0",
        ),
        ARVStaker(
            address=ADDRESSES[1],
            arv_holding="200",
            rewards="0",
        ),
    ]
    voters = ADDRESSES[0]

    accounts = init_account_rewards(stakers, voters, config)

    assert len(accounts) == 2
    assert accounts[0].address == ADDRESSES[0]
    assert accounts[0].state == AccountState.ACTIVE
    assert accounts[0].rewards == config.reward_token(amount="0")
    assert accounts[1].address == ADDRESSES[1]
    assert accounts[1].state == AccountState.INACTIVE
    assert accounts[1].rewards == config.reward_token(amount="0")


def test_tokens_by_status(ADDRESSES, config):
    accounts = [
        Account(
            address=ADDRESSES[0],
            token=ARV(amount="100"),
            state=AccountState.ACTIVE,
            rewards=config.reward_token(amount="0"),
        ),
        Account(
            token=ARV(amount="200"),
            address=ADDRESSES[1],
            state=AccountState.INACTIVE,
            rewards=config.reward_token(amount="0"),
        ),
    ]

    assert tokens_by_status(accounts, AccountState.ACTIVE) == Decimal("100")
    assert tokens_by_status(accounts, AccountState.INACTIVE) == Decimal("200")
    assert tokens_by_status(accounts, None) == Decimal("300")

    stats = compute_token_stats(accounts)

    assert stats.total == "300"
    assert stats.active == "100"
    assert stats.inactive == "200"


def test_distribute(ADDRESSES, config):
    stakers = [
        ARVStaker(
            address=ADDRESSES[0],
            arv_holding="100",
            rewards="0",
        ),
        ARVStaker(
            address=ADDRESSES[1],
            arv_holding="200",
            rewards="0",
        ),
    ]
    voters = ADDRESSES[0]
    distribution, summary, token_stats = distribute(config, stakers, voters)

    assert all(isinstance(acc, Account) for acc in distribution)
    assert all(
        acc.state == AccountState.ACTIVE
        if acc.address in voters
        else AccountState.INACTIVE
        for acc in distribution
    )

    assert all(
        acc.rewards == config.reward_token(amount=acc.rewards.amount)
        for acc in distribution
    )

    assert token_stats.total == "300"
    assert token_stats.active == "100"
    assert token_stats.inactive == "200"

    assert summary.amount == str(config.arv_rewards)
    assert summary.address == config.reward_token().address
    assert summary.symbol == config.reward_token().symbol
