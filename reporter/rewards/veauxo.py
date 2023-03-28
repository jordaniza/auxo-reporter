import datetime
from decimal import Decimal, getcontext
from typing import Optional, Tuple

from reporter import utils
from reporter.config import load_conf
from reporter.env import ADDRESSES
from reporter.errors import MissingStakingManagerAddressError
from reporter.models import (
    Account,
    AccountState,
    Config,
    ARVStaker,
    TokenSummaryStats,
    EthereumAddress,
    RewardSummary,
    Staker,
    ARVRewardSummary,
)
from reporter.queries import get_veauxo_stakers, get_vote_data
from reporter.writer import write_accounts_and_distribution, write_arv_stats
from reporter.rewards.common import compute_rewards


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


def separate_xauxo_rewards(
    staking_manager: Account,
    reward_summaries: ARVRewardSummary,
    accounts: list[Account],
) -> Tuple[ARVRewardSummary, list[Account]]:
    reward_summaries.amount = str(
        int(reward_summaries.amount) - int(staking_manager.rewards.amount)
    )
    reward_summaries.to_xauxo = staking_manager.rewards.amount

    accounts = list(filter(lambda a: a.address != staking_manager.address, accounts))

    return reward_summaries, accounts
