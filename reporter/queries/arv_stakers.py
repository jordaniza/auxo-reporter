import json
from typing import Any, Union, cast

from multicall import Call, Multicall  # type: ignore

from reporter.env import ADDRESSES
from reporter.errors import MissingBoostBalanceException
from reporter.models import Config, EthereumAddress, ARVStaker, ARV
from reporter.queries.common import get_token_hodlers, w3

"""
ARV Stakers get their total balance from the DecayOracle. 
We simply need the list of holders, which we fetch from the graph.
At time of writing, we store both their `original_holdings` (without the DecayOracle)
as well as their decayed/boosted balance, which is what we use to calculate rewards
"""


def get_arv_stakers(conf: Config) -> list[ARVStaker]:
    """
    Fetch the list of ARV token holders at the given block number
    """
    arv: list[Any] = get_token_hodlers(conf, ADDRESSES.ARV)
    return [ARVStaker(v["valueExact"], address=v["account"]["id"]) for v in arv]


MulticallReturnBoost = dict[EthereumAddress, Union[int, str]]


def get_boosted_lock(
    stakers: list[ARVStaker], block_number: int, mock=False
) -> MulticallReturnBoost:
    """
    Multicall out to the DecayOracle to fetch the boosted/decayed balance of ARV for each address
    """

    if mock:
        with open("reporter/test/scenario_testing/decay_veauxo.json") as j:
            mock_multicall_response = json.load(j)
        return mock_multicall_response

    calls = [
        Call(
            # address to call:
            ADDRESSES.DECAY_ORACLE,  # this needs to be the oracle address
            # signature + return value, with argument:
            ["balanceOf(address)(uint256)", s.address],
            # return in a format of {[address]: uint}:
            [[s.address, None]],
        )
        for s in stakers
    ]

    # Immediately execute the multicall
    return Multicall(calls, _w3=w3, block_id=block_number)()


def apply_boost(
    stakers: list[ARVStaker], boost_dict: MulticallReturnBoost
) -> list[ARVStaker]:
    """
    Creates a new list of stakers with the boosted balance added
    Applies a caveat to the staking manager, who is responsible for holding PRV rewards
    and is therefore exempt from boosting requirements.
    """

    new_stakers: list[ARVStaker] = []
    for s in stakers:
        # avoid pass by reference
        boosted_balance = boost_dict[cast(str, s.address)]

        # we should always be able to find the stakers, throw if not
        if not boosted_balance:
            raise MissingBoostBalanceException(
                f"Missing Boosted Balance for Staker, {s.address}"
            )

        # store original amount for reference
        cast(ARV, s.token).decayed_amount = str(boosted_balance)
        new_stakers.append(s)

    return new_stakers


def boost_stakers(stakers: list[ARVStaker], mock=False) -> list[ARVStaker]:
    boost_data = get_boosted_lock(stakers, mock)
    return apply_boost(stakers, boost_data)


def get_arv_stakers_and_boost(config: Config) -> list[ARVStaker]:
    stakers = get_arv_stakers(config)
    return boost_stakers(stakers, config.block_snapshot)