import datetime
import itertools
import functools
from decimal import Decimal, getcontext
from typing import Tuple, Optional
from tinydb import TinyDB

from reporter import utils
from reporter.conf_generator import load_conf
from reporter.types import (
    Vote,
    Staker,
    Proposal,
    Account,
    AccountState,
    Config,
    Reward,
    VeTokenStats,
    RewardSummary,
    BaseReward,
)
from reporter.voters import get_vote_data
from reporter.queries import get_stakers


def init_account_rewards(
    stakers: list[Staker], voters: list[str], conf: Config
) -> list[Account]:
    """
    Create the base Account object from a list of stakers.
    Rewards will be added later based on the account state.
    :param `stakers`: all vetoken stakers
    :param `voters`: list of all accounts that voted that month
    """
    return [
        Account(
            address=staker.id,
            vetoken_balance=staker.accountVeTokenBalance,
            state=AccountState.ACTIVE if staker.id in voters else AccountState.SLASHED,
            rewards="0",
        )
        for staker in stakers
    ]


def distribute_rewards(account: Account, pro_rata: Decimal, reward: Reward) -> Account:
    """
    Add the rewards for he account, for a particular token.
    :param `account`: the account to add rewards to
    :param `pro_rata`: quantity of reward token to be add per vetoken units held by account
    :param `reward`: the token to be added

    Slashed accounts will be appended a reward entry with an amount equal to zero
    """

    if account.state == AccountState.ACTIVE:
        account_reward = int(
            pro_rata * Decimal(account.vetoken_balance) / Decimal(10**reward.decimals)
        )
        account.rewards = str(account_reward)

    return account


def compute_rewards(
    reward: Reward, total_active_vetokens: Decimal, accounts: list[Account]
) -> RewardSummary:
    """

    Add the rewards per user
    :param `total_rewards`: rewards token with total quantities to distribute amongst stakers
    :param `total_active_vetokens`: vetokens belonging to non-slashed stakers
    :param `accounts`: base array of Account objects that have yet to have rewards added
    """

    # compute rewards per veToken held, for the given reward token
    pro_rata = (Decimal(reward.amount) / total_active_vetokens) * Decimal(
        10**reward.decimals
    )

    # append rewards to existing accounts for this token
    accounts = list(
        map(
            distribute_rewards,
            accounts,
            itertools.repeat(pro_rata),
            itertools.repeat(reward),
        )
    )

    # add to summary
    distribution_rewards = RewardSummary(
        **reward.dict(),
        pro_rata=str(pro_rata),
    )

    # TODO remainder?
    return distribution_rewards


def vetokens_by_status(
    accounts: list[Account], state: Optional[AccountState] = None
) -> Decimal:
    """helper mehod to get total veTokens by active or slashed"""
    accounts_to_summarize = accounts
    if state:
        accounts_to_summarize = utils.filter_state(accounts, state)
    return functools.reduce(
        lambda running_total, account: running_total + Decimal(account.vetoken_balance),
        accounts_to_summarize,
        Decimal(0),
    )


def compute_veToken_stats(accounts: list[Account]) -> VeTokenStats:
    """Summarize veToken balances for storage in the DB"""
    total_active_vetokens = vetokens_by_status(accounts, AccountState.ACTIVE)
    total_slashed_vetokens = vetokens_by_status(accounts, AccountState.SLASHED)
    total_vetokens = vetokens_by_status(accounts, None)

    veTokenStats = VeTokenStats(
        total=str(int(total_vetokens)),
        active=str(int(total_active_vetokens)),
        slashed=str(int(total_slashed_vetokens)),
    )
    return veTokenStats


def distribute(
    conf: Config, accounts: list[Account]
) -> Tuple[list[Account], RewardSummary, VeTokenStats]:
    """Compute the distribution for all accounts, and summarize the data"""

    veToken_stats = compute_veToken_stats(accounts)
    distribution_rewards = compute_rewards(
        conf.rewards, Decimal(veToken_stats.active), accounts
    )

    return (accounts, distribution_rewards, veToken_stats)


def write_governance_stats(
    db: TinyDB,
    stakers: list[Staker],
    votes: list[Vote],
    proposals: list[Proposal],
    voters: list[str],
    non_voters: list[str],
    rewards: RewardSummary,
    veTokenStats: VeTokenStats,
):
    db.table("governance_stats").insert(
        {
            "stakers": [s.dict() for s in stakers],
            "votes": [v.dict() for v in votes],
            "proposals": [p.dict() for p in proposals],
            "voters": voters,
            "non_voters": non_voters,
            "rewards": rewards.dict(),
            "veTokenStats": veTokenStats.dict(),
        },
    )


def write_accounts_and_distribution(
    db: TinyDB, accounts: list[Account], distribution: list[Account]
):
    db.table("accounts").insert_multiple([a.dict() for a in accounts])
    db.table("distribution").insert_multiple([d.dict() for d in distribution])


def main(path: Optional[str]):
    if not path:
        path = input(" Path to the config file ")

    conf = load_conf(path)

    getcontext().prec = 42

    db = utils.get_db(path, drop=True)

    start_date = datetime.date.fromtimestamp(conf.start_timestamp)
    end_date = datetime.date.fromtimestamp(conf.end_timestamp)
    print(f"⚗ Building database from {start_date} to {end_date}...")

    stakers = get_stakers(conf)

    (votes, proposals, voters, non_voters) = get_vote_data(conf, stakers)

    accounts = init_account_rewards(stakers, voters, conf)
    (distribution, reward_summaries, vetoken_stats) = distribute(conf, accounts)
    write_accounts_and_distribution(db, accounts, distribution)
    write_governance_stats(
        db,
        stakers,
        votes,
        proposals,
        voters,
        non_voters,
        reward_summaries,
        vetoken_stats,
    )
