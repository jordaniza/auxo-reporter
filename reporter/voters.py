from typing import Tuple

from pydantic import parse_obj_as

from reporter import utils
from reporter.models import (
    Config,
    Delegate,
    OnChainProposal,
    OnChainVote,
    Proposal,
    Staker,
    Vote,
)
from reporter.queries import get_delegates, get_on_chain_votes, get_votes


def parse_votes(conf: Config) -> list[Vote]:
    """Deserialize votes fetched from API to an array of Vote objects"""
    return parse_obj_as(list[Vote], get_votes(conf))


def parse_on_chain_votes(conf: Config) -> list[OnChainVote]:
    return parse_obj_as(list[OnChainVote], get_on_chain_votes(conf))


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


def filter_votes_by_proposal(
    votes: list[Vote],
) -> Tuple[list[Vote], list[Proposal]]:
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


def get_voters(
    votes: list[Vote], stakers: list[Staker], delegates: list[Delegate]
) -> Tuple[list[str], list[str]]:
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


def get_vote_data(
    conf: Config, stakers: list[Staker]
) -> Tuple[list[Vote], list[Proposal], list[str], list[str]]:
    """
    Fetch all information related to voting this month and return a tuple with required info
    :returns:
        * list of all votes
        * list of all valid proposals
        * list of addresses of active voters
        * list of addresses of inactive voters
    """
    votes = parse_votes(conf)
    on_chain_votes = parse_on_chain_votes(conf)

    combined_votes = combine_on_off_chain_votes(votes, on_chain_votes)
    (filtered_votes, proposals) = filter_votes_by_proposal(combined_votes)

    delegates = get_delegates()
    (voters, non_voters) = get_voters(filtered_votes, stakers, delegates)

    return (filtered_votes, proposals, voters, non_voters)
