import json
import pytest
import functools
from decimal import Decimal
from pydantic import parse_obj_as
from reporter.queries import *
from eth_utils import to_checksum_address
from reporter.models import (
    OnChainVote,
    Account,
    AccountState,
    Delegate,
)
from reporter import utils
from reporter.test.conftest import _addresses


@pytest.fixture(autouse=True)
def before_each(monkeypatch):
    """don't filter proposals based on user input"""
    monkeypatch.setattr("builtins.input", lambda _: False)
    yield


DELEGATE = Delegate(delegator=_addresses[0], delegate=_addresses[1])


def init_mocks(monkeypatch):
    with open("reporter/test/stubs/tokens/arv.json") as j:
        mock_stakers = json.load(j)

    with open("reporter/test/stubs/snapshot-votes.json") as j:
        mock_votes = json.load(j)

    with open("reporter/test/stubs/delegates.json") as j:
        mock_delegates = json.load(j)

    with open("reporter/test/stubs/votes/onchain-votes.json") as j:
        mock_on_chain_votes = json.load(j)

    """
    When patching, you need to specify the file where the function is *executed*
    As opposed to where it was defined. See this SO answer:
    https://stackoverflow.com/questions/31306080/pytest-monkeypatch-isnt-working-on-imported-function
    """
    monkeypatch.setattr(
        "reporter.queries.graphql_iterate_query",
        lambda url, access_path, params: mock_stakers["data"]["erc20Contract"][
            "balances"
        ],
    )
    monkeypatch.setattr("reporter.queries.get_votes", lambda _: mock_votes)
    monkeypatch.setattr(
        "reporter.queries.get_delegates",
        lambda: parse_obj_as(list[Delegate], mock_delegates),
    )

    monkeypatch.setattr(
        "reporter.queries.parse_onchain_votes",
        lambda _: parse_obj_as(
            list[OnChainVote], mock_on_chain_votes["data"]["voteCasts"]
        ),
    )

    monkeypatch.setattr("reporter.queries.get_delegates", [DELEGATE])

    return (mock_stakers, mock_votes, mock_delegates)


def test_get_arv_stakers(monkeypatch, config):
    init_mocks(monkeypatch)

    stakers = get_arv_stakers(config)

    assert all(to_checksum_address(s.address) == s.address for s in stakers)


def test_get_voters(monkeypatch, config):
    with open("reporter/test/stubs/snapshot-votes.json") as j:
        mock_votes = json.load(j)

    monkeypatch.setattr("reporter.queries.get_votes", lambda _: mock_votes)

    voters = parse_offchain_votes(config)
    assert len(voters) == len(mock_votes)


def test_get_vote_data(config, monkeypatch):

    init_mocks(monkeypatch)
    stakers = get_arv_stakers(config)
    votes, proposals = get_votes(config)
    voters, non_voters = get_voters(votes, stakers)
    voter_ids = [v.voter for v in votes]

    assert len(proposals) == 4
    assert len(voters) + len(non_voters) == len(stakers) + len([DELEGATE])
    assert all(voter in voter_ids for voter in voters)


def no_slashed_has_rewards(distribution: list[Account]) -> bool:
    slashed = utils.filter_state(distribution, AccountState.INACTIVE)
    return all(int(s.rewards.amount) == 0 for s in slashed)


def all_active_have_rewards(distribution: list[Account]) -> bool:
    slashed = utils.filter_state(distribution, AccountState.ACTIVE)
    return all(int(s.rewards.amount) > 0 for s in slashed)


def sum_totals(distribution: list[Account]) -> Decimal:
    account_rewards = [a.rewards for a in distribution]
    return functools.reduce(
        lambda acc, curr: acc + Decimal(curr.amount), account_rewards, Decimal(0)
    )
