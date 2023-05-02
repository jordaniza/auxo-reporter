from copy import deepcopy
from typing import Any, TypedDict, TypeVar, cast

import requests
from web3 import Web3

from reporter.env import RPC_URL, SUBGRAPHS
from reporter.errors import EmptyQueryError, TooManyLoopsError
from reporter.models import GraphQL_Response, Config, EthereumAddress

w3 = Web3(Web3.HTTPProvider(RPC_URL))


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
    url: str, access_path: list[str], params: GraphQLConfig, max_loops: int = 1000
) -> list[T]:
    """
    The graph allows fetching of Max 1000 results for subgraphs.
    This function chunks queries into batches then stops when it returns no results
    :param `url`: the subgraph endpoint
    :param `access_path`: eg ['erc20accounts', 'balances'] - set of keys to fetch data
    :param `params`: GraphQL config such as the actual query and variables
    """

    response: GraphQL_Response = requests.post(url, json=params).json()

    if not response:
        raise EmptyQueryError(f"No results for graph query to {url}")
    if "errors" in response:
        raise EmptyQueryError(
            f"Error in graph query to {url}: {cast(dict, response)['errors']}"
        )

    all_results: list[T] = extract_nested_graphql(response, access_path)

    current_batch = all_results
    loops = 0
    while len(current_batch) > 0:
        if loops > max_loops:
            raise TooManyLoopsError("graphql_iterate_query")
        params["variables"]["skip"] = len(current_batch)
        response = requests.post(url, json=params).json()
        current_batch = extract_nested_graphql(response, access_path)
        all_results += current_batch
        loops += 1
    return all_results


def get_token_hodlers(conf: Config, token_address: EthereumAddress) -> list:
    """
    Fetch holders along with total balances grom the graph.
    This can be used for Auxo, ARV and PRV but bear in mind that:
    - ARV balances are subject to decay (for the purposes of rewards)
    - PRV balances may be deposited into the RollStaker
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
        SUBGRAPHS.AUXO_STAKING,
        ["erc20Contract", "balances"],
        dict(query=query, variables=variables),
    )
