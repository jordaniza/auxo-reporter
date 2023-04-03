from decimal import Decimal, getcontext
from reporter.config import load_conf
from reporter.models import (
    DB,
    Writer,
    Config,
    RedistributionContainer,
    PRVRewardSummary,
)
from reporter.errors import MissingDBException
from reporter.queries import (
    get_prv_total_supply,
    get_prv_accounts,
)
from reporter.rewards import (
    compute_prv_token_stats,
    compute_rewards,
    prv_active_rewards,
    create_prv_reward_summary,
    redistribute,
)

getcontext().prec = 42


def initialize_container(inactive: Decimal, config: Config) -> RedistributionContainer:
    container = RedistributionContainer(redistributions=config.redistributions)
    container.redistribute(inactive)
    return container


def run_prv(path_to_config) -> None:

    # load the config file
    config = load_conf(path_to_config)
    writer = Writer(config)
    path = f"reports/{config.date}"

    if not DB.exists(f"{path}/reporter-db.json"):
        raise MissingDBException(
            f"Missing DB at f{path}, please run the ARV distribution first"
        )
    # don't drop the DB as we rely on it
    db = DB(config, drop=False)

    # compute supply at the passed block
    supply = get_prv_total_supply(config.block_snapshot)

    # fetch the list of accounts and compute active vs. total
    accounts = get_prv_accounts(config)

    # compute the stats for the PRV token
    prv_stats = compute_prv_token_stats(accounts, supply)

    # redistribute rewards accruing to inactive stakers
    (active_rewards, inactive_rewards) = prv_active_rewards(prv_stats, config)

    container = initialize_container(inactive_rewards, config)
    accounts_redistributed = redistribute(accounts, container, config)

    distribution, distribution_rewards = compute_rewards(
        config.reward_token(amount=str(active_rewards + container.to_stakers)),
        Decimal(prv_stats.active),  # active PRV not rewards
        accounts_redistributed,
    )

    # yield the summary for reporting
    summary = create_prv_reward_summary(distribution_rewards, container)

    # update the DB and create claims
    db.write_prv_stats(
        accounts,
        summary,
        prv_stats,
    )
    db.write_claims_and_distribution(distribution, "PRV")

    # write our data to individual CSV and JSON files
    writer.to_csv_and_json([s.dict() for s in accounts], "PRV_stakers")
