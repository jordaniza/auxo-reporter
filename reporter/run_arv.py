from decimal import getcontext
from reporter.config import load_conf
from reporter.models import (
    ARVRewardSummary,
    DB,
    Writer,
)
from reporter.queries import (
    get_arv_stakers_and_boost,
    get_voters,
    get_votes,
)

from reporter.rewards import distribute


# set the context for decimal precision to avoid scientific notation
getcontext().prec = 42


def run_arv(path_to_config) -> None:
    """
    The main() function is the entry point of the program and is responsible
    for orchestrating the various steps of the ARV token distribution process.
    """

    # load the configuration file
    config = load_conf(path_to_config)

    # create a Writer object to write output files
    writer = Writer(config)

    # instantiate a fresh DB
    db = DB(config, drop=True)

    # fetch ARV Stakers
    stakers = get_arv_stakers_and_boost(config)

    # fetch votes and proposals
    votes, proposals = get_votes(config)

    # separate voters from non-voters
    voters, non_voters = get_voters(votes, stakers)

    # compute the distribution of ARV tokens
    distribution, reward_summaries, stats = distribute(config, stakers, voters)

    # update the DB and create claims
    db.write_claims_and_distribution(distribution, "ARV")
    db.write_arv_stats(
        stakers,
        votes,
        proposals,
        voters,
        non_voters,
        reward_summaries,
        stats,
    )

    # write our data to individual CSV and JSON files
    writer.to_csv_and_json([s.dict() for s in stakers], "ARV_stakers")
    writer.to_csv_and_json([v.dict() for v in votes], "votes")
    writer.to_csv_and_json([p.dict() for p in proposals], "proposals")
    writer.lists_to_csv_and_json([("voters", voters), ("non_voters", non_voters)])
