import json
from typing import Literal

from multicall import Call, Multicall  # type: ignore

from reporter.env import ADDRESSES
from reporter.models import (
    Account,
    AccountState,
    Config,
    EthereumAddress,
    Staker,
    PRVStaker,
)
from reporter.queries.common import SUBGRAPHS, graphql_iterate_query, w3

"""
We calculate PRV differently to ARV. ARV rewards are distributed to active voters, PRV rewards
are only distributed to actively staked PRV holders. 

This means we can't just lookup PRV holders - people who are fully staked and earning rewards will have 
a balance of zero. We need to instead look at who is deposited, and check their balance in the contract.
"""


def get_all_prv_depositors() -> list[dict[Literal["user"], EthereumAddress]]:
    """
    This function returns a simple list of every user that has ever staked xAUXO to earn rewards.
    This will include inactive users, or those who have unstaked.

    Therefore, ensure you check the user's balance to see that they actually have "actively" staked
    tokens (in the current epoch) before assigning rewards.

    In future releases, we may streamline the Subgraph to properly track xAUXO balances but this approach
    should suffice for the time being.
    """
    query = """
    query( $skip: Int ) { 
        depositeds(skip: $skip, first: 1000) { 
            user 
        } 
    }
    """
    # this also needs to be at the block number
    return graphql_iterate_query(
        SUBGRAPHS.ROLLSTAKER,
        ["depositeds"],
        dict(query=query, variables={"skip": 0}),
    )


def get_prv_staked_balances(
    stakers: list[EthereumAddress],
    conf: Config,
) -> dict[EthereumAddress, str]:
    """
    For a given list of stakers, fetch the balance in the current epoch that is earning rewards
    """

    calls = [
        Call(
            # address to call:
            ADDRESSES.PRV_ROLLSTAKER,
            # signature + return value, with argument:
            ["getCurrentBalanceForUser(address)(uint256)", s],
            # return in a format of {[address]: uint256}:
            [[s, None]],
        )
        for s in stakers
    ]

    # Immediately execute the multicall
    # need to add the block number here
    return Multicall(calls, _w3=w3, block_id=conf.block_snapshot)()


def get_prv_stakers(conf: Config) -> list[PRVStaker]:
    """
    Fetch a list of all accounts that have ever made deposits in the RollStaker contract
    Then filter to just those with a currently active balance of > 1
    """

    all_depositors_ever = [d["user"] for d in get_all_prv_depositors()]
    prv_balances = get_prv_staked_balances(all_depositors_ever, conf)
    return [
        Staker.xAuxo(addr, staked)
        for addr, staked in prv_balances.items()
        if int(staked) > 0
    ]


def prv_stakers_to_accounts(stakers: list[Staker], conf: Config) -> list[Account]:
    """
    Convert a list of PRV stakers into Accounts by initializing an empty reward balance
    Then setting them to ACTIVE.

    We know PRV holders are ACTIVE because we have fetched only active holders.
    """
    empty_reward = Config.reward_token(conf)
    return [
        Account.from_staker(
            staker=staker,
            rewards=empty_reward,
            state=AccountState.ACTIVE,
        )
        for staker in stakers
    ]


def get_prv_accounts(conf: Config) -> list[Account]:
    stakers = get_prv_stakers(conf)
    return prv_stakers_to_accounts(stakers, conf)
