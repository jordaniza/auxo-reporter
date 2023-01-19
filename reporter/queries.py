import json
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, TypedDict, TypeVar, cast, Union

import requests
from multicall import Call, Multicall  # type: ignore
from pydantic import parse_obj_as
from web3 import Web3

from reporter.env import ADDRESSES, RPC_URL, SNAPSHOT_SPACE_ID
from reporter.errors import EmptyQueryError, MissingDecayBalanceException
from reporter.models import (
    Account,
    AccountState,
    Config,
    Delegate,
    EthereumAddress,
    GraphQL_Response,
    OnChainProposal,
    Staker,
)


@dataclass
class SUBGRAPHS:
    GRAPH_URL = "https://api.thegraph.com/subgraphs/name"
    SNAPSHOT = "https://hub.snapshot.org/graphql"
    VEDOUGH = GRAPH_URL + "/pie-dao/vedough"

    # prototype - absolutely no guarantees of uptime or api consistency
    AUXO_TOKEN_GOERLI = GRAPH_URL + "/jordaniza/auxo-tokens-v2"
    AUXO_GOV_GOERLI = GRAPH_URL + "/jordaniza/auxo-gov-goerli-1"


class GraphQLConfig(TypedDict):
    """
    Typechecker for JSON/Dict data to be passed to the graph
    :param `query`: the query to send to The Graph
    :param `variables`: injected query params in dictionary format
    """

    query: str
    variables: dict[str, Any]


# python insantiates generics separate to function definition
T = TypeVar("T")


def extract_nested_graphql(res: GraphQL_Response, access_path: list[str]):
    """
    This function walks through a dictionary until it finds the data you want.

    For the graphql queries, this is typically an array of values that is limited in size
    (eg: we can only fetch 1000 accounts at a time)

    :param `access_path`: in the format ['first_key', 'nested_key_level0', 'nested_key_level1', ....]
    :param `res`: api response from graphql. First key should be 'data'
    """
    deepcopy_access_path = deepcopy(access_path)
    current = res["data"]
    while len(deepcopy_access_path) > 0:
        current = current[deepcopy_access_path.pop(0)]
    return current


def graphql_iterate_query(
    url: str, access_path: list[str], params: GraphQLConfig
) -> list[T]:
    """
    The graph allows fetching of Max 1000 results for subgraphs.
    This function chunks queries into batches then stops when it returns no results
    :param `url`: the subgraph endpoint
    :param `access_path`: eg ['erc20accounts', 'balances'] - set of keys to fetch data
    :param `params`: GraphQL config such as the actual query and variables
    """

    # bit of a wobbly cast here as errors will crash the runtime
    res: GraphQL_Response = requests.post(url, json=params).json()
    if not res:
        raise EmptyQueryError(f"No results for graph query to {url}")

    results: list[T] = extract_nested_graphql(res, access_path)

    container = results
    # WARNING: Mocking requests.post here will result in an infinite loop
    while len(container) > 0:
        params["variables"]["skip"] = len(container)
        res = requests.post(url, json=params).json()
        container = extract_nested_graphql(res, access_path)
        results += container
    return results


def get_votes(conf: Config):
    """Fetch snapshot votes for the DAO between start and end timestamps in config object"""

    votes_query = """
        query($skip: Int, $space: String, $created_gte: Int, $created_lte: Int) { 
            votes(skip: $skip, first: 1000, where: {space: $space, created_gte: $created_gte, created_lte: $created_lte}) {
                voter
                choice
                created
                proposal {
                    id
                    title
                    author
                    created
                    start
                    end
                    choices
                }
            }
        }
    """

    variables = {
        "skip": 0,
        "space": SNAPSHOT_SPACE_ID,
        "created_gte": conf.start_timestamp,
        "created_lte": conf.end_timestamp,
    }

    votes: list[Any] = graphql_iterate_query(
        SUBGRAPHS.SNAPSHOT, ["votes"], dict(query=votes_query, variables=variables)
    )
    return votes


def get_delegates() -> list[Delegate]:
    """Fetches list of whitelisted delegate/delegator pairs"""

    query = "{ delegates(first: 1000) { delegator, delegate } }"
    delegates = requests.post(SUBGRAPHS.VEDOUGH, json={"query": query})
    delegate_data = delegates.json().get("data")
    return parse_obj_as(list[Delegate], delegate_data.get("delegates"))


def get_on_chain_votes(conf: Config):
    """
    Grab vote proposals and votes from OZ Governor
    """

    votes_query = """
    query($governor: String, $timestamp_gt: Int, $timestamp_lte: Int, $skip: Int) {
        voteCasts(
            first: 1000
            skip: $skip
            where: { 
                timestamp_gt: $timestamp_gt,
                timestamp_lte: $timestamp_lte,
                governor: $governor
            }
        ) {
            id
            receipt {
                reason
            }
            support {
                support
            }
            proposal {
                description
                canceled
                executed
                id
                endBlock
                startBlock
                proposer {
                    id
                }
                proposalCreated {
                    timestamp
                }
            }
            governor {
                id
            }
            voter {
                id
            }
            timestamp
        }     
    }
    """

    variables = {
        "skip": 0,
        "governor": ADDRESSES.GOVERNOR,
        "timestamp_gt": conf.start_timestamp,
        "timestamp_lte": conf.end_timestamp,
    }
    votes: list[Any] = graphql_iterate_query(
        SUBGRAPHS.AUXO_GOV_GOERLI,
        ["voteCasts"],
        dict(query=votes_query, variables=variables),
    )
    return votes


def to_proposal(proposal_data) -> OnChainProposal:
    return parse_obj_as(OnChainProposal, proposal_data)


def get_token_hodlers(conf: Config, token_address: EthereumAddress) -> list:
    """
    Fetch balances of token in `token_address` at a given block number.
    """
    query = """
        query($token: String, $block: Int, $skip: Int) {
            erc20Contract(
                id: $token,
                block: {number: $block}
            ) {
                decimals
                id
                name
                symbol      
                totalSupply {
                    value
                    valueExact
                }
                balances(
                    orderBy: valueExact
                    orderDirection: desc
                    where: {account_not: null, valueExact_gt: 0}
                    first: 1000
                    skip: $skip
                ) {
                    account {
                        id
                    }
                    value
                    valueExact
                }
            }
        }
    """
    variables = {
        "token": token_address,
        "block": conf.block_snapshot,
        "skip": 0,
    }
    return graphql_iterate_query(
        SUBGRAPHS.AUXO_TOKEN_GOERLI,
        ["erc20Contract", "balances"],
        dict(query=query, variables=variables),
    )


def get_xauxo_stakers(conf: Config) -> list[Staker]:
    """
    Fetch the list of xAUXO token holders at the given block number
    """

    x_auxo: list[Any] = get_token_hodlers(conf, ADDRESSES.XAUXO)
    return [Staker.xAuxo(x["account"]["id"], x["valueExact"]) for x in x_auxo]


def get_veauxo_stakers(conf: Config):
    """
    Fetch the list of veAUXO token holders at the given block number
    """
    ve_auxo: list[Any] = get_token_hodlers(conf, ADDRESSES.VEAUXO)
    return [Staker.veAuxo(v["account"]["id"], v["valueExact"]) for v in ve_auxo]


def get_stakers(conf: Config):
    return (get_veauxo_stakers(conf), get_xauxo_stakers(conf))


def get_x_auxo_statuses(
    stakers: list[Staker], mock=False
) -> dict[EthereumAddress, bool]:
    """
    For a passed list of xAUXO holders, we make a multicall to the
    xAUXO staker contract to check if they are active in the current epoch or not.
    """
    if mock:
        with open("reporter/test/scenario_testing/xauxo_stakers.json") as j:
            mock_multicall_response = json.load(j)
        return mock_multicall_response

    # instantiate a basic web3 client from the environment
    w3 = Web3(Web3.HTTPProvider(RPC_URL))

    calls = [
        Call(
            # address to call:
            ADDRESSES.XAUXO_ROLLSTAKER,
            # signature + return value, with argument:
            # TODO - do we need to call a specific epoch here?
            ["userIsActive(address)(bool)", s.address],
            # return in a format of {[address]: bool}:
            [[s.address, None]],
        )
        for s in stakers
    ]

    # Immediately execute the multicall
    return Multicall(calls, _w3=w3)()


def get_xauxo_active_state(
    staker: Staker, statuses: dict[EthereumAddress, bool]
) -> AccountState:
    address = cast(
        EthereumAddress, staker.address
    )  # TODO change data model to avoid this cast
    xauxo_status: bool = statuses[address]
    return AccountState.ACTIVE if xauxo_status else AccountState.INACTIVE


def xauxo_accounts(
    stakers: list[Staker], statuses: dict[EthereumAddress, bool], conf: Config
) -> list[Account]:
    empty_reward = Config.reward_token(conf)
    return [
        Account.from_staker(
            staker=staker,
            rewards=empty_reward,
            state=get_xauxo_active_state(staker, statuses),
        )
        for staker in stakers
    ]


MulticallReturnDecay = dict[EthereumAddress, Union[int, str]]


def get_veauxo_boosted_balance_by_staker(
    stakers: list[Staker], mock=False
) -> MulticallReturnDecay:
    if mock:
        with open("reporter/test/scenario_testing/decay_veauxo.json") as j:
            mock_multicall_response = json.load(j)
        return mock_multicall_response

    # instantiate a basic web3 client from the environment
    w3 = Web3(Web3.HTTPProvider(RPC_URL))

    calls = [
        Call(
            # address to call:
            ADDRESSES.DECAY_ORACLE,  # this needs to be the oracle address
            # signature + return value, with argument:
            # TODO - do we need to call a specific epoch here?
            ["balanceOf(address)(uint256)", s.address],
            # return in a format of {[address]: uint}:
            [[s.address, None]],
        )
        for s in stakers
    ]

    # Immediately execute the multicall
    return Multicall(calls, _w3=w3)()


def get_boosted_veauxo_balance(
    stakers: list[Staker], decay_dict: MulticallReturnDecay
) -> list[Staker]:

    new_stakers: list[Staker] = []
    for s in stakers:
        new_s = deepcopy(s)
        boosted_balance = decay_dict[cast(str, new_s.address)]
        if not boosted_balance:
            raise MissingDecayBalanceException(
                f"Missing Decayed Balance for Staker, {new_s.address}"
            )
        # staking manager will never get decayed
        if s.address == ADDRESSES.STAKING_MANAGER:
            new_s.holding.original_amount = new_s.holding.amount
        else:
            # cache original amount for reference
            new_s.holding.original_amount = new_s.holding.amount
            new_s.holding.amount = str(boosted_balance)
        new_stakers.append(new_s)

    return new_stakers


def get_boosted_stakers(stakers: list[Staker]) -> list[Staker]:
    decay_data = get_veauxo_boosted_balance_by_staker(stakers)
    return get_boosted_veauxo_balance(stakers, decay_data)
