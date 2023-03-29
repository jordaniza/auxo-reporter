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
from reporter.rewards import distribute
from reporter.errors import MissingDBException


getcontext().prec = 42
from reporter.queries import (
    get_prv_stakers,
    prv_stakers_to_accounts,
    get_prv_total_supply,
)
from reporter.rewards.xauxo import (
    compute_prv_token_stats,
    prv_active_rewards,
    normalize_redistributions,
    create_prv_reward_summary,
    redistribute,
)

import datetime
import json
from copy import deepcopy
from decimal import Decimal, getcontext

import pytest
from pydantic import parse_obj_as

from reporter import utils
from reporter.config import load_conf
from reporter.env import ADDRESSES
from reporter.models import (
    Delegate,
    OnChainVote,
    RedistributionOption,
    RedistributionWeight,
    RedistributionContainer,
    TokenSummaryStats,
    Vote,
    Staker,
    ARVRewardSummary,
    XAuxoRewardSummary,
)
from reporter.queries import (
    prv_stakers_to_accounts,
    get_prv_accounts,
    get_prv_total_supply,
)
from reporter.rewards import compute_rewards

from reporter.writer import (
    build_claims,
    write_accounts_and_distribution,
    write_xauxo_stats,
)


def initialize_container(inactive: Decimal, config: Config) -> RedistributionContainer:
    container = RedistributionContainer(_redistributions=config.redistributions)
    container.redistribute(inactive)
    return container


def main(path_to_config) -> None:

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
    (active_rewards, inactive_rewards) = prv_active_rewards(
        prv_stats, config.prv_rewards
    )

    # redistribute rewards accruing to inactive stakers
    container = initialize_container(inactive_rewards, config)
    accounts_redistributed = redistribute(accounts, container, config)

    # action the rewards distribution across xauxo stakers
    stakers_erc20 = config.reward_token(str(int(container.to_stakers)))
    rewarded_accounts, distribution_rewards = compute_rewards(
        stakers_erc20,
        Decimal(prv_stats.active),  # active PRV not rewards
        accounts_redistributed,
    )

    # yield the summary for reporting
    summary = create_prv_reward_summary(distribution_rewards, container)

    # write_xauxo_stats(db, xauxo_accounts_out, xauxo_distribution_rewards, xauxo_stats)
    # write_accounts_and_distribution(db, xauxo_accounts_out, xauxo_accounts_out, "xAUXO")
    # build_claims(config, db, "reporter/test/stubs/db", "xAUXO")
