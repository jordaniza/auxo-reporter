import json
from copy import deepcopy
from typing import Any, Union, cast

from multicall import Call, Multicall  # type: ignore

from reporter.env import ADDRESSES
from reporter.errors import MissingDecayBalanceException
from reporter.models import Config, EthereumAddress, Staker, ARVStaker
from reporter.queries.common import get_token_hodlers, w3

"""
veAUXO Stakers get their total balance from the DecayOracle. 
We simply need the list of holders, which we fetch from the graph.
At time of writing, we store both their `original_holdings` (without the DecayOracle)
as well as their decayed/boosted balance, which is what we use to calculate rewards
"""


def get_veauxo_stakers(conf: Config) -> list[ARVStaker]:
    """
    Fetch the list of veAUXO token holders at the given block number
    """
    ve_auxo: list[Any] = get_token_hodlers(conf, ADDRESSES.VEAUXO)
    return [ARVStaker(v["valueExact"], address=v["account"]["id"]) for v in ve_auxo]


MulticallReturnDecay = dict[EthereumAddress, Union[int, str]]


def get_veauxo_boosted_balance_by_staker(
    stakers: list[ARVStaker], block_number: int, mock=False
) -> MulticallReturnDecay:
    """
    Multicall out to the DecayOracle to fetch the boosted/decayed balance of veAUXO for each address
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


def get_boosted_veauxo_balance(
    stakers: list[ARVStaker], decay_dict: MulticallReturnDecay
) -> list[ARVStaker]:
    """
    Creates a new list of stakers with the decayed balance added
    Applies a caveat to the staking manager, who is responsible for holding xAUXO rewards
    and is therefore exempt from boosting requirements.
    """

    new_stakers: list[ARVStaker] = []
    for s in stakers:
        # avoid pass by reference
        boosted_balance = decay_dict[cast(str, s.address)]

        # we should always be able to find the stakers, throw if not
        if not boosted_balance:
            raise MissingDecayBalanceException(
                f"Missing Decayed Balance for Staker, {s.address}"
            )

        # store original amount for reference
        s.token.decayed_amount = str(boosted_balance)
        new_stakers.append(s)

    return new_stakers


def get_boosted_stakers(stakers: list[ARVStaker], mock=False) -> list[ARVStaker]:
    decay_data = get_veauxo_boosted_balance_by_staker(stakers, mock)
    return get_boosted_veauxo_balance(stakers, decay_data)
