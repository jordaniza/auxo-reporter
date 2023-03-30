from decimal import Decimal
from typing import Optional, Tuple

from reporter import utils
from reporter.models import (
    Account,
    AccountState,
    Config,
    ARVStaker,
    TokenSummaryStats,
    RewardSummary,
)
from reporter.rewards import compute_rewards


def init_account_rewards(
    stakers: list[ARVStaker], voters: list[str], conf: Config
) -> list[Account]:
    """
    Create the base Account object from a list of stakers.
    Rewards will be added later based on the account state.

    :param `stakers`: all vetoken stakers
    :param `voters`: list of all accounts that voted that month
    """
    return [
        Account.from_arv_staker(
            staker,
            state=AccountState.ACTIVE
            if staker.address in voters
            else AccountState.INACTIVE,
            rewards=conf.reward_token(),
        )
        for staker in stakers
    ]


def tokens_by_status(
    accounts: list[Account], state: Optional[AccountState] = None
) -> Decimal:
    """helper mehod to get total staked holdings by active or inactive"""
    accounts_to_summarize = accounts

    if state:
        accounts_to_summarize = utils.filter_state(accounts, state)

    return Decimal(
        sum(Decimal(account.token.amount) for account in accounts_to_summarize)
    )


def compute_token_stats(accounts: list[Account]) -> TokenSummaryStats:
    """Summarize token balances by state"""
    total_active_tokens = tokens_by_status(accounts, AccountState.ACTIVE)
    total_inactive_tokens = tokens_by_status(accounts, AccountState.INACTIVE)
    total_tokens = tokens_by_status(accounts, None)

    tokenStats = TokenSummaryStats(
        total=str(int(total_tokens)),
        active=str(int(total_active_tokens)),
        inactive=str(int(total_inactive_tokens)),
    )
    return tokenStats


def distribute(
    conf: Config, stakers: list[ARVStaker], voters: list[str]
) -> Tuple[list[Account], RewardSummary, TokenSummaryStats]:
    """Compute the distribution for all accounts, and summarize the data"""

    accounts = init_account_rewards(stakers, voters, conf)
    token_stats = compute_token_stats(accounts)
    distribution, distribution_rewards = compute_rewards(
        conf.rewards, Decimal(token_stats.active), accounts
    )

    return (distribution, distribution_rewards, token_stats)
