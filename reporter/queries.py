import requests
import os
from dataclasses import dataclass
from typing import TypeVar, Any, TypedDict
from pydantic import parse_obj_as
from dotenv import load_dotenv

from reporter.errors import EmptyQueryError
from reporter.types import Config, Staker, Delegate, OnChainVote, OnChainProposal
from utils import env_var


SNAPSHOT_SPACE_ID = env_var("SNAPSHOT_SPACE_ID")
GOVERNOR_ADDRESS = env_var("GOVERNOR_ADDRESS")


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

from pprint import pprint


def graphql_iterate_query(url: str, accessor: str, params: GraphQLConfig) -> list[T]:
    """
    The graph allows fetching of Max 1000 results for subgraphs.
    This function chunks queries into batches then stops when it returns no results
    :param `url`: the subgraph endpoint
    :param `accessor`: our data is contained under `res['data'][accessor]`
    :param `params`: GraphQL config such as the actual query and variables
    """
    res: dict[str, Any] = requests.post(url, json=params).json()
    if not res:
        raise EmptyQueryError(f"No results for graph query to {url}")

    results: list[T] = res["data"][accessor]
    container = results
    # WARNING: Mocking requests.post here will result in an infinite loop
    while len(container) > 0:
        params["variables"]["skip"] = len(container)
        res = requests.post(url, json=params).json()
        container = res["data"][accessor]
        results += container
    return results


# How to fix the 'first' problem with > 1000 stakers
def get_stakers(conf: Config) -> list[Staker]:
    """Fetch a list of veToken stakers at a given block number"""

    query = f"{{ stakers(first: 1000, block: {{number: {conf.block_snapshot}}}) {{ id, accountVeTokenBalance }} }}"
    graphQl_response = (
        requests.post(url=SUBGRAPHS.VEDOUGH, json={"query": query}).json().get("data")
    )
    return parse_obj_as(list[Staker], graphQl_response.get("stakers"))


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
        SUBGRAPHS.SNAPSHOT, "votes", dict(query=votes_query, variables=variables)
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
        "governor": GOVERNOR_ADDRESS,
        "timestamp_gt": conf.start_timestamp,
        "timestamp_lte": conf.end_timestamp,
    }
    votes: list[Any] = graphql_iterate_query(
        SUBGRAPHS.AUXO_GOV_GOERLI,
        "voteCasts",
        dict(query=votes_query, variables=variables),
    )
    return votes


def to_proposal(proposal_data) -> OnChainProposal:
    return parse_obj_as(OnChainProposal, proposal_data)


def on_chain_votes_to_votes(data_in: list[Any]) -> list[OnChainVote]:
    return parse_obj_as(list[OnChainVote], data_in)


def get_token_holders():
    """
    All the holders of all the tokens.
    This can and will be optimized.
    """
    query = """
        query($skip: Int) {
            accounts(
                first: 1000, 
                skip: $skip, 
                where: {ERC20balances_: {valueExact_gt: "0"}}
            ) {
                id
                ERC20balances {
                    value
                    contract {
                        name
                        symbol
                        id
                    }
                    valueExact
                }
            }
        }
    """
    return graphql_iterate_query(
        SUBGRAPHS.AUXO_TOKEN_GOERLI,
        "accounts",
        dict(query=query, variables={"skip": 0}),
    )
