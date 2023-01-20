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
    TokenSummaryStats,
    EthereumAddress,
    RewardSummary,
    Staker,
    VeAuxoRewardSummary,
)
from reporter.queries import get_veauxo_stakers, get_vote_data
from reporter.writer import write_accounts_and_distribution, write_veauxo_stats
from reporter.rewards.common import compute_rewards


def init_account_rewards(
    stakers: list[Staker], voters: list[str], conf: Config
) -> list[Account]:
    """
    Create the base Account object from a list of stakers.
    Rewards will be added later based on the account state.

    Staking manager is always considered an active voter.

    :param `stakers`: all vetoken stakers
    :param `voters`: list of all accounts that voted that month
    """
    return [
        Account.from_staker(
            staker,
            state=AccountState.ACTIVE
            if staker.address
            in voters + [ADDRESSES.STAKING_MANAGER]  # shorthand for appending
            else AccountState.INACTIVE,
            rewards=conf.reward_token(),
        )
        for staker in stakers
    ]


def separate_staking_manager(
    accounts: list[Account], address: EthereumAddress = ADDRESSES.STAKING_MANAGER
) -> Tuple[list[Account], Account]:
    """
    The staking manager handles all veAUXO deposited as a result of xAUXO.
    Therefore, the staking manager's rewards should be removed from veAUXO and allocated to xAUXO

    This function fetches the staking manager from the accounts so we can use its rewards as the basis for xAUXO
    """
    try:
        for idx, a in enumerate(accounts):
            if a.address == address:
                staking_manager = accounts[idx]
                # staking manager is always active
                accounts[idx].state = AccountState.ACTIVE

        return accounts, staking_manager
    except (StopIteration, UnboundLocalError):
        raise MissingStakingManagerAddressError(
            f"Could not find staking manager with address {address}"
        )


def tokens_by_status(
    accounts: list[Account], state: Optional[AccountState] = None
) -> Decimal:
    """helper mehod to get total staked holdings by active or inactive"""
    accounts_to_summarize = accounts

    if state:
        accounts_to_summarize = utils.filter_state(accounts, state)

    return Decimal(
        sum(Decimal(account.holding.amount) for account in accounts_to_summarize)
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
    conf: Config, accounts: list[Account]
) -> Tuple[list[Account], RewardSummary, TokenSummaryStats]:
    """Compute the distribution for all accounts, and summarize the data"""

    token_stats = compute_token_stats(accounts)
    accounts, distribution_rewards = compute_rewards(
        conf.rewards, Decimal(token_stats.active), accounts
    )

    return (accounts, distribution_rewards, token_stats)


def separate_xauxo_rewards(
    staking_manager: Account,
    reward_summaries: VeAuxoRewardSummary,
    accounts: list[Account],
) -> Tuple[VeAuxoRewardSummary, list[Account]]:
    reward_summaries.amount = str(
        int(reward_summaries.amount) - int(staking_manager.rewards.amount)
    )
    reward_summaries.to_xauxo = staking_manager.rewards.amount

    accounts = list(filter(lambda a: a.address != staking_manager.address, accounts))

    return reward_summaries, accounts


def main(path: Optional[str]):
    """
    Distribution for veAUXO
    """

    if not path:
        path = input(" Path to the config file ")

    conf = load_conf(path)

    getcontext().prec = 42

    db = utils.get_db(path, drop=True)

    start_date = datetime.date.fromtimestamp(conf.start_timestamp)
    end_date = datetime.date.fromtimestamp(conf.end_timestamp)
    print(f"⚗ Building database from {start_date} to {end_date}...")

    stakers = get_veauxo_stakers(conf)

    (votes, proposals, voters, non_voters) = get_vote_data(conf, stakers)

    accounts = init_account_rewards(stakers, voters, conf)

    # save staking manager separately and remove its rewards from the veAUXO Tree
    # this needs to be done BEFORE we do any slashing as the staking manager isn't required to vote
    # alternatively, we set the SM to active
    (accounts, staking_manager) = separate_staking_manager(accounts)
    (distribution, reward_summaries, vetoken_stats) = distribute(conf, accounts)

    (reward_summaries, accounts) = separate_xauxo_rewards(
        staking_manager, VeAuxoRewardSummary(**reward_summaries.dict()), accounts
    )

    write_accounts_and_distribution(db, accounts, distribution)
    write_veauxo_stats(
        db,
        stakers,
        votes,
        proposals,
        voters,
        non_voters,
        reward_summaries,
        vetoken_stats,
        staking_manager,
    )
