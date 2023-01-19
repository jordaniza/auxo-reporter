import datetime
import json
from copy import deepcopy
from decimal import Decimal, getcontext

import pytest
from pydantic import parse_obj_as

from reporter import utils
from reporter.conf_generator import load_conf
from reporter.env import ADDRESSES
from reporter.models import (
    Delegate,
    OnChainVote,
    RedistributionOption,
    RedistributionWeight,
    VeAuxoRewardSummary,
    Staker,
    XAuxoRewardSummary,
)
from reporter.queries import (
    get_veauxo_stakers,
    get_x_auxo_statuses,
    get_stakers,
    get_xauxo_stakers,
    xauxo_accounts,
)
from reporter.rewards import (
    compute_rewards,
    distribute,
    get_vote_data,
    init_account_rewards,
    separate_staking_manager,
    separate_xauxo_rewards,
    write_accounts_and_distribution,
    write_veauxo_stats,
    write_xauxo_stats,
)
from reporter.xAuxo.rewards import compute_allocations, compute_x_auxo_reward_total
from reporter.test.conftest import mock_token_holders
from reporter.writer import build_claims


@pytest.fixture(autouse=True)
def before_each(monkeypatch):
    """don't filter proposals based on user input"""
    monkeypatch.setattr("builtins.input", lambda _: False)
    yield


root = "reporter/test/scenario_testing"


def init_mocks(monkeypatch):
    with open(f"{root}/votes_on.json") as j:
        mock_on_chain_votes = json.load(j)

    with open(f"{root}/votes_off.json") as j:
        mock_votes = json.load(j)

    with open("reporter/test/stubs/delegates.json") as j:
        mock_delegates = []

    # get_x_auxo_statuses
    with open(f"{root}/mock_xauxo.json") as j:
        mock_xauxo_holders = json.load(j)

    # get_x_auxo_statuses
    with open(f"{root}/mock_veauxo.json") as j:
        mock_veauxo_holders = json.load(j)

    """
    When patching, you need to specify the file where the function is *executed*
    As opposed to where it was defined. See this SO answer:
    https://stackoverflow.com/questions/31306080/pytest-monkeypatch-isnt-working-on-imported-function
    """
    monkeypatch.setattr("reporter.voters.get_votes", lambda _: mock_votes)
    monkeypatch.setattr(
        "reporter.voters.get_delegates",
        lambda: parse_obj_as(list[Delegate], mock_delegates),
    )
    monkeypatch.setattr(
        "reporter.voters.parse_on_chain_votes",
        lambda conf: parse_obj_as(
            list[OnChainVote], mock_on_chain_votes["data"]["voteCasts"]
        ),
    )

    monkeypatch.setattr(
        "reporter.queries.get_xauxo_stakers",
        lambda conf: [
            Staker.xAuxo(x["account"]["id"], x["valueExact"])
            for x in mock_xauxo_holders["data"]["erc20Contract"]["balances"]
        ],
    )

    monkeypatch.setattr(
        "reporter.queries.get_veauxo_stakers",
        lambda conf: [
            Staker.veAuxo(v["account"]["id"], v["valueExact"])
            for v in mock_veauxo_holders["data"]["erc20Contract"]["balances"]
        ],
    )

    return (mock_votes, mock_delegates, mock_veauxo_holders)


def test_do_not_require_address_for_redistribute():
    r1 = RedistributionWeight(
        weight=1, address=None, option=RedistributionOption.REDISTRIBUTE_XAUXO
    )

    r2 = RedistributionWeight(
        weight=1, address=None, option=RedistributionOption.REDISTRIBUTE_VEAUXO
    )

    assert not r1.address
    assert not r2.address


def test_both(monkeypatch):
    config = load_conf("reporter/test/scenario_testing")

    getcontext().prec = 42

    db = utils.get_db("reporter/test/stubs/db", drop=True)

    start_date = datetime.date.fromtimestamp(config.start_timestamp)
    end_date = datetime.date.fromtimestamp(config.end_timestamp)
    print(f"⚗ Building database from {start_date} to {end_date}...")

    init_mocks(monkeypatch)

    (veauxo_stakers, xauxo_stakers) = get_stakers(config)

    (votes, proposals, voters, non_voters) = get_vote_data(config, veauxo_stakers)
    veauxo_accounts_in = init_account_rewards(veauxo_stakers, voters, config)

    # save staking manager separately
    (veauxo_accounts_out, staking_manager) = separate_staking_manager(
        veauxo_accounts_in, ADDRESSES.STAKING_MANAGER
    )

    (veauxo_distribution, veauxo_reward_summaries, veauxo_stats) = distribute(
        config, veauxo_accounts_out
    )

    #  and remove its rewards from the veAUXO Tree
    (veauxo_reward_summaries, veauxo_accounts_out) = separate_xauxo_rewards(
        staking_manager,
        VeAuxoRewardSummary(**veauxo_reward_summaries.dict()),
        veauxo_accounts_out,
    )

    write_accounts_and_distribution(db, veauxo_accounts_out, veauxo_distribution)
    write_veauxo_stats(
        db,
        veauxo_stakers,
        votes,
        proposals,
        voters,
        non_voters,
        veauxo_reward_summaries,
        veauxo_stats,
        staking_manager,
    )
    build_claims(config, db, "reporter/test/stubs/db", "veAUXO")

    xauxo_active = get_x_auxo_statuses(xauxo_stakers, mock=True)
    xauxo_accounts_in = xauxo_accounts(xauxo_stakers, xauxo_active, config)

    xauxo_rewards_total_no_haircut = deepcopy(config.rewards)
    xauxo_rewards_total_no_haircut.amount = veauxo_reward_summaries.to_xauxo

    xauxo_redistributions = config.redistributions

    (xauxo_rewards_total_with_haircut, xauxo_haircut) = compute_x_auxo_reward_total(
        config, Decimal(xauxo_rewards_total_no_haircut.amount)
    )

    (
        xauxo_stats,
        xauxo_accounts_out,
        _,
        stakers_rewards,
        redistributed_to_stakers,
        redistributed_transfer,
    ) = compute_allocations(
        xauxo_accounts_in,
        xauxo_rewards_total_with_haircut,
        xauxo_redistributions,
        config,
    )

    xauxo_stakers_net_redistributed = deepcopy(config.rewards)
    xauxo_stakers_net_redistributed.amount = str(int(stakers_rewards))

    distribution_rewards = compute_rewards(
        xauxo_stakers_net_redistributed,
        Decimal(xauxo_stats.active),
        xauxo_accounts_out,
    )

    xauxo_distribution_rewards = XAuxoRewardSummary(
        **distribution_rewards.dict(),
    )
    xauxo_distribution_rewards.total_haircut = str(xauxo_haircut)
    xauxo_distribution_rewards.amount = str(
        int(float(xauxo_rewards_total_with_haircut.amount))
    )
    xauxo_distribution_rewards.redistributed_to_stakers = redistributed_to_stakers
    xauxo_distribution_rewards.redistributed_total = str(
        int(Decimal(redistributed_to_stakers) + redistributed_transfer)
    )
    xauxo_distribution_rewards.redistributed_transferred = str(
        int(redistributed_transfer)
    )

    write_xauxo_stats(
        db, xauxo_accounts_out, xauxo_distribution_rewards, xauxo_stats, staking_manager
    )
    write_accounts_and_distribution(db, xauxo_accounts_out, xauxo_accounts_out, "xAUXO")
    build_claims(config, db, "reporter/test/stubs/db", "xAUXO")
