import datetime
import itertools
import functools
from decimal import Decimal, getcontext
from typing import Tuple, Optional, Union, Literal
from tinydb import TinyDB

from reporter import utils
from reporter.conf_generator import load_conf, STAKING_MANAGER_ADDRESS, VEAUXO_ADDRESS
from reporter.types import (
    Vote,
    Staker,
    Proposal,
    AUXO_TOKEN_NAMES,
    Account,
    AccountState,
    EthereumAddress,
    Config,
    ERC20Metadata,
    TokenSummaryStats,
    VeAuxoRewardSummary,
    RewardSummary,
    XAuxoRewardSummary,
    VeAuxoRewardSummary,
    BaseERC20Holding,
)
from reporter.voters import get_vote_data
from reporter.queries import get_stakers
from reporter.errors import MissingStakingManagerAddressError


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
            token=BaseERC20Holding(
                amount=staker.accountVeTokenBalance, address=VEAUXO_ADDRESS
            ),
            state=AccountState.ACTIVE if staker.id in voters else AccountState.INACTIVE,
            rewards="0",
        )
        for staker in stakers
    ]


def distribute_rewards(
    account: Account, pro_rata: Decimal, reward: ERC20Metadata
) -> Account:
    """
    Add the rewards for he account, for a particular token.
    :param `account`: the account to add rewards to
    :param `pro_rata`: quantity of reward token to be add per vetoken units held by account
    :param `reward`: the token to be added

    Slashed accounts will be appended a reward entry with an amount equal to zero
    """

    if account.state == AccountState.ACTIVE:
        account_reward = int(
            pro_rata * Decimal(account.token.amount) / Decimal(10**reward.decimals)
        )
        account.rewards = str(Decimal(account.rewards) + account_reward)
        account.notes.append(f"active reward of {account_reward}")

    return account


def compute_rewards(
    total_rewards: ERC20Metadata, total_active_tokens: Decimal, accounts: list[Account]
) -> RewardSummary:
    """

    Add the rewards that will be distributed across all users, including the pro-rata reward rate for each token
    Modifies the accounts object to add rewards

    TODO: side-effect is a bit weird and would be better as a pure function

    :param `total_rewards`: rewards token with total quantities to distribute amongst stakers
    :param `total_active_tokens`: tokens belonging to active stakers (total - inactive)
    :param `accounts`: base array of Account objects that have yet to have rewards added
    """

    # compute rewards per veToken held, for the given reward token
    pro_rata = (Decimal(total_rewards.amount) / total_active_tokens) * Decimal(
        10**total_rewards.decimals
    )

    # append rewards to existing accounts for this token
    accounts = list(
        map(
            distribute_rewards,
            accounts,
            itertools.repeat(pro_rata),
            itertools.repeat(total_rewards),
        )
    )

    # add to summary
    distribution_rewards = RewardSummary(
        **total_rewards.dict(),
        pro_rata=str(pro_rata),
    )

    # TODO remainder?
    return distribution_rewards


def tokens_by_status(
    accounts: list[Account], state: Optional[AccountState] = None
) -> Decimal:
    """helper mehod to get total veTokens by active or slashed"""
    accounts_to_summarize = accounts
    if state:
        accounts_to_summarize = utils.filter_state(accounts, state)
    return functools.reduce(
        lambda running_total, account: running_total + Decimal(account.token.amount),
        accounts_to_summarize,
        Decimal(0),
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
    distribution_rewards = compute_rewards(
        conf.rewards, Decimal(token_stats.active), accounts
    )

    return (accounts, distribution_rewards, token_stats)


def write_veauxo_stats(
    db: TinyDB,
    stakers: list[Staker],
    votes: list[Vote],
    proposals: list[Proposal],
    voters: list[str],
    non_voters: list[str],
    rewards: VeAuxoRewardSummary,
    tokenStats: TokenSummaryStats,
    staking_manager: Account,
):
    db.table("veAUXO_stats").insert(
        {
            "stakers": [s.dict() for s in stakers],
            "votes": [v.dict() for v in votes],
            "proposals": [p.dict() for p in proposals],
            "voters": voters,
            "non_voters": non_voters,
            "rewards": rewards.dict(),
            "token_stats": tokenStats.dict(),
            "staking_manager": staking_manager.dict(),
        },
    )


def write_xauxo_stats(
    db: TinyDB,
    accounts: list[Account],
    rewards: XAuxoRewardSummary,
    tokenStats: TokenSummaryStats,
    staking_manager: Account,
):
    db.table("xAUXO_stats").insert(
        {
            "stakers": [a.dict() for a in accounts],
            "rewards": rewards.dict(),
            "token_stats": tokenStats.dict(),
            "staking_manager": staking_manager.dict(),
        },
    )


def write_accounts_and_distribution(
    db: TinyDB,
    accounts: list[Account],
    distribution: list[Account],
    token_name: AUXO_TOKEN_NAMES = "veAUXO",
):
    db.table(f"{token_name}_holders").insert_multiple([a.dict() for a in accounts])
    db.table(f"{token_name}_distribution").insert_multiple(
        [d.dict() for d in distribution]
    )


def separate_staking_manager(
    accounts: list[Account], address: EthereumAddress = STAKING_MANAGER_ADDRESS
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
    except StopIteration:
        raise MissingStakingManagerAddressError(
            f"Could not find staking manager with address {address}"
        )


def separate_xauxo_rewards(
    staking_manager: Account,
    reward_summaries: VeAuxoRewardSummary,
    accounts: list[Account],
) -> Tuple[VeAuxoRewardSummary, list[Account]]:
    reward_summaries.amount = str(
        int(reward_summaries.amount) - int(staking_manager.rewards)
    )
    reward_summaries.to_xauxo = staking_manager.rewards

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

    stakers = get_stakers(conf)

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
