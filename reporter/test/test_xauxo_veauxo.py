import functools
import pytest
import json
import datetime
from eth_utils import to_checksum_address
from pydantic import parse_obj_as
from decimal import Decimal, getcontext

from reporter.test.conftest import MockResponse

from reporter import utils
from reporter.rewards import (
    get_vote_data,
    init_account_rewards,
    distribute,
    write_accounts_and_distribution,
    write_veauxo_stats,
    compute_rewards,
    separate_staking_manager,
    write_xauxo_stats,
    separate_xauxo_rewards,
)
from reporter.voters import parse_votes, get_voters
from reporter.queries import get_stakers
from reporter.types import (
    AccountState,
    Config,
    Delegate,
    Account,
    Vote,
    Staker,
    VeAuxoRewardSummary,
    XAuxoRewardSummary,
)
from reporter.queries import xauxo_accounts, get_x_auxo_statuses, get_xauxo_hodlers
from reporter.xAuxo.rewards import (
    RedistributionWeight,
    compute_x_auxo_reward_total,
    RedistributionOption,
    compute_allocations,
    compute_xauxo_rewards,
    load_redistributions,
    ERROR_MESSAGES,
    NormalizedRedistributionWeight,
    compute_token_stats,
)

from pydantic import ValidationError
from reporter.test.conftest import mock_token_holders
from pprint import pprint
from reporter.writer import build_claims
from decimal import Decimal
from reporter.errors import BadConfigException
from reporter.types import AccountState, Config, ERC20Metadata
from reporter.conf_generator import X_AUXO_HAIRCUT_PERCENT, XAUXO_ADDRESS
from reporter.test.conftest import LIVE_CALLS_DISABLED, SKIP_REASON
from reporter import utils
from copy import deepcopy


@pytest.fixture(autouse=True)
def before_each(monkeypatch):
    """don't filter proposals based on user input"""
    monkeypatch.setattr("builtins.input", lambda _: False)
    yield


def init_mocks(monkeypatch):
    with open("reporter/test/stubs/stakers-subgraph-response.json") as j:
        mock_stakers = json.load(j)

    with open("reporter/test/stubs/snapshot-votes.json") as j:
        mock_votes = json.load(j)

    with open("reporter/test/stubs/delegates.json") as j:
        mock_delegates = json.load(j)

    """
    When patching, you need to specify the file where the function is *executed*
    As opposed to where it was defined. See this SO answer:
    https://stackoverflow.com/questions/31306080/pytest-monkeypatch-isnt-working-on-imported-function
    """
    monkeypatch.setattr("requests.post", lambda url, json: MockResponse(mock_stakers))
    monkeypatch.setattr("reporter.voters.get_votes", lambda _: mock_votes)
    monkeypatch.setattr(
        "reporter.voters.get_delegates",
        lambda: parse_obj_as(list[Delegate], mock_delegates),
    )

    return (mock_stakers, mock_votes, mock_delegates)


def test_do_not_require_address_for_redistribute():
    r1 = RedistributionWeight(
        weight=1, address=None, option=RedistributionOption.REDISTRIBUTE_XAUXO
    )

    r2 = RedistributionWeight(
        weight=1, address=None, option=RedistributionOption.REDISTRIBUTE_VEAUXO
    )

    assert not r1.address
    assert not r2.address


def mock_ve_auxo_holders(monkeypatch) -> None:
    return mock_token_holders(monkeypatch, "reporter/test/stubs/tokens/veauxo.json")


def test_both(config: Config, monkeypatch):

    getcontext().prec = 42

    db = utils.get_db("reporter/test/stubs/db", drop=True)

    start_date = datetime.date.fromtimestamp(config.start_timestamp)
    end_date = datetime.date.fromtimestamp(config.end_timestamp)
    print(f"⚗ Building database from {start_date} to {end_date}...")

    init_mocks(monkeypatch)
    veauxo_stakers = get_stakers(config)
    (votes, proposals, voters, non_voters) = get_vote_data(config, veauxo_stakers)
    veauxo_accounts_in = init_account_rewards(veauxo_stakers, voters, config)

    # save staking manager separately
    (veauxo_accounts_out, staking_manager) = separate_staking_manager(
        veauxo_accounts_in, veauxo_accounts_in[1].address
    )

    (veauxo_distribution, veauxo_reward_summaries, veauxo_stats) = distribute(
        config, veauxo_accounts_out
    )
    print(veauxo_stats)

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

    # xauxo
    mock_ve_auxo_holders(monkeypatch)

    xauxo_holders = get_xauxo_hodlers(config)
    xauxo_active = get_x_auxo_statuses(xauxo_holders)
    xauxo_accounts_in = xauxo_accounts(xauxo_holders, xauxo_active)

    xauxo_rewards_total_no_haircut = deepcopy(config.rewards)
    xauxo_rewards_total_no_haircut.amount = veauxo_reward_summaries.to_xauxo

    xauxo_redistributions = load_redistributions(
        "reporter/test/stubs/config/redistributions.json"
    )

    (xauxo_rewards_total_with_haircut, xauxo_haircut) = compute_x_auxo_reward_total(
        Decimal(xauxo_rewards_total_no_haircut.amount)
    )

    (
        xauxo_stats,
        xauxo_accounts_out,
        redistributions,
        stakers_rewards,
        redistributed_to_stakers,
        redistributed_transfer,
    ) = compute_allocations(
        xauxo_accounts_in, xauxo_rewards_total_with_haircut, xauxo_redistributions
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
