from typing import Any

import requests
from pydantic import parse_obj_as

import reporter.utils as utils
from reporter.env import ADDRESSES, SNAPSHOT_SPACE_ID
from reporter.models import (
    Config,
    Delegate,
    Vote,
    Proposal,
    OnChainProposal,
    OnChainVote,
    Staker,
)
from reporter.queries.common import SUBGRAPHS, graphql_iterate_query


def get_offchain_votes(conf: Config):
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


def get_onchain_votes(conf: Config) -> list:
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


def filter_votes_by_proposal(
    votes: list[Vote],
) -> tuple[list[Vote], list[Proposal]]:
    """
    Prompt the operator to remove invalid proposals this month
    :param `votes`: list of all votes
    :returns: A tuple of valid votes and proposals
    """

    unique_proposals = {v.proposal.id: v.proposal for v in votes}
    if utils.yes_or_no("Do you want to filter proposals?"):
        proposals = []
        proposals_ids = []
        for p in unique_proposals.values():

            if utils.yes_or_no(f"Is proposal {p.title} a valid proposal?"):
                proposals.append(p)
                proposals_ids.append(p.id)

        return ([v for v in votes if v.proposal.id in proposals_ids], proposals)

    else:
        return (votes, list(unique_proposals.values()))


def get_delegates() -> list[Delegate]:
    """Fetches list of whitelisted delegate/delegator pairs"""

    query = "{ delegates(first: 1000) { delegator, delegate } }"
    delegates = requests.post(SUBGRAPHS.VEDOUGH, json={"query": query})
    delegate_data = delegates.json().get("data")
    return parse_obj_as(list[Delegate], delegate_data.get("delegates"))


def get_voters(
    votes: list[Vote], stakers: list[Staker], delegates: list[Delegate]
) -> tuple[list[str], list[str]]:
    """
    Compare the list of `stakers` to the list of `votes` to see who has/has not voted this month.
    Also factors in delegated votes for whitelisted accounts.
    :returns: 2 lists:
        * First is all addresses that voted
        * Second is all addresses that have not voted
    """
    voters = set([v.voter for v in votes])
    stakers_addrs = [s.address for s in stakers]

    stakers_addrs_no_delegators = [
        addr for addr in stakers_addrs if addr not in delegates
    ]

    voted = [addr for addr in stakers_addrs_no_delegators if addr in voters] + [
        d.delegator for d in delegates if d.delegate in voters
    ]

    not_voted = [addr for addr in stakers_addrs_no_delegators if addr not in voters] + [
        d.delegator for d in delegates if d.delegate not in voters
    ]

    return (utils.unique(voted), utils.unique(not_voted))


def parse_offchain_votes(conf: Config) -> list[Vote]:
    return parse_obj_as(list[Vote], get_offchain_votes(conf))


def parse_onchain_votes(conf: Config) -> list[OnChainVote]:
    return parse_obj_as(list[OnChainVote], get_onchain_votes(conf))


def combine_on_off_chain_proposals(
    offchain: list[Proposal], onchain: list[OnChainProposal]
) -> list[Proposal]:

    coerced = [ocp.coerce_to_proposal() for ocp in onchain]
    return offchain + coerced


def combine_on_off_chain_votes(
    offchain: list[Vote], onchain: list[OnChainVote]
) -> list[Vote]:

    coerced = [ocv.coerce_to_vote() for ocv in onchain]
    return offchain + coerced


def get_vote_data(
    conf: Config, stakers: list[Staker]
) -> tuple[list[Vote], list[Proposal], list[str], list[str]]:
    """
    Fetch all information related to voting this month and return a tuple with required info
    :returns:
        * list of all votes
        * list of all valid proposals
        * list of addresses of active voters
        * list of addresses of inactive voters
    """
    offchain_votes = parse_offchain_votes(conf)
    onchain_votes = parse_onchain_votes(conf)

    combined_votes = combine_on_off_chain_votes(offchain_votes, onchain_votes)

    (filtered_votes, proposals) = filter_votes_by_proposal(combined_votes)

    delegates = get_delegates()
    (voters, non_voters) = get_voters(filtered_votes, stakers, delegates)

    return (filtered_votes, proposals, voters, non_voters)
