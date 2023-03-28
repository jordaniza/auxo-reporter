import json
from typing import Literal

from multicall import Call, Multicall  # type: ignore

from reporter.env import ADDRESSES
from reporter.models import Account, AccountState, Config, EthereumAddress, Staker
from reporter.queries.common import SUBGRAPHS, graphql_iterate_query, w3

"""
We calculate xAUXO differently to veAUXO. veAUXO rewards are distributed to tokenHolders, xAUXO rewards
are only distributed to actively staked xAUXO holders. 

This means we can't just lookup xAUXO holders - people who are fully staked and earning rewards will have 
a balance of zero. We need to instead look at who is deposited, and check their balance in the contract.
"""


def get_all_xauxo_depositors() -> list[dict[Literal["user"], EthereumAddress]]:
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
    return graphql_iterate_query(
        SUBGRAPHS.ROLLSTAKER,
        ["depositeds"],
        dict(query=query, variables={"skip": 0}),
    )


def get_xauxo_staked_balances(
    stakers: list[EthereumAddress],
) -> dict[EthereumAddress, str]:
    """
    For a given list of stakers, fetch the balance in the current epoch that is earning rewards
    """

    calls = [
        Call(
            # address to call:
            ADDRESSES.XAUXO_ROLLSTAKER,
            # signature + return value, with argument:
            ["getCurrentBalanceForUser(address)(uint256)", s],
            # return in a format of {[address]: uint256}:
            [[s, None]],
        )
        for s in stakers
    ]

    # Immediately execute the multicall
    return Multicall(calls, _w3=w3)()


def get_xauxo_stakers() -> list[Staker]:
    """
    Fetch a list of all accounts that have ever made deposits in the RollStaker contract
    Then filter to just those with a currently active balance of > 1
    """

    all_depositors_ever = [d["user"] for d in get_all_xauxo_depositors()]
    x_auxo_stakers_with_balances = get_xauxo_staked_balances(all_depositors_ever)
    return [
        Staker.xAuxo(addr, staked)
        for addr, staked in x_auxo_stakers_with_balances.items()
        if int(staked) > 0
    ]


def xauxo_accounts(stakers: list[Staker], conf: Config) -> list[Account]:
    """
    Convert a list of xAUXO stakers into Accounts by initializing an empty reward balance
    Then setting them to ACTIVE.

    We know xAUXO holders are ACTIVE because we have fetched only active holders.
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
