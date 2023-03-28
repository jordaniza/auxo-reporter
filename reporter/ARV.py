"""
Begins from a config file and computes the ARV distribution
    - Load the config: 70% of distribution goes to ARV
    - Fetch ARV stakers and save
    - Fetch and write the first DB entry:
        - Recipient: ARV Balance, Auxo Lock Balance, Boosted ARV Balance, Time remaining, block snapshot
    - Fetch and write the second DB entry:
        - This is just a combination of on and offchain votes
    - Take the existing data for delegates, stakers and votes and write the 3rd DB entry
        - Active and Inactive recipients
    - Get rid of the staking manager logic, we don’t need
    - Apply distribution logic
    - Write claims to the claims file
"""
from decimal import getcontext

from reporter.config import load_conf
from reporter.models import (
    ARVRewardSummary,
    DB,
    Writer,
    Config,
    ARVStaker,
)
from reporter.queries import (
    get_boosted_stakers,
    get_veauxo_stakers,
    get_voters,
    get_votes,
)
from reporter.rewards import (
    distribute,
    init_account_rewards,
)

# set the context for decimal precision to avoid scientific notation
getcontext().prec = 42


def get_ARV_stakers(config: Config) -> list[ARVStaker]:
    veauxo_stakers_pre_decay = get_veauxo_stakers(config)
    return get_boosted_stakers(veauxo_stakers_pre_decay, config.block_snapshot)


def main(path_to_config) -> None:
    """
    Main entry point for the ARV distribution
    """

    # load the config file
    config = load_conf(path_to_config)
    writer = Writer(config)
    path = f"reports/{config.date}"
    db = DB(path, drop=True)

    # fetch ARV Stakers
    stakers = get_ARV_stakers(config)

    # fetch votes and proposals
    (votes, proposals) = get_votes(config)
    (voters, non_voters) = get_voters(votes, stakers)

    # finally compute the distribution
    (distribution, reward_summaries, stats) = distribute(config, stakers, voters)

    # update the DB and write claims
    db.write_distribution(distribution, "ARV")
    db.write_arv_stats(
        stakers,
        votes,
        proposals,
        voters,
        non_voters,
        ARVRewardSummary.from_existing(reward_summaries),
        stats,
    )
    db.build_claims(config.distribution_window, "ARV")

    # write some stats for easy debugging and viewing
    writer.to_csv_and_json([s.dict() for s in stakers], "ARV_stakers")
    writer.to_csv_and_json([v.dict() for v in votes], "votes")
    writer.to_csv_and_json([p.dict() for p in proposals], "proposals")
    writer.to_csv_and_json([{"voters": v} for v in voters], "voters")
    writer.to_csv_and_json([{"non_voters": v} for v in non_voters], "non_voters")
