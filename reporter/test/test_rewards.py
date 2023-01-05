import functools
import pytest
import json
import datetime
from eth_utils import to_checksum_address
from dataclasses import dataclass
from typing import Any
from pydantic import parse_obj_as
from decimal import Decimal, getcontext

from reporter import utils
from reporter.rewards import (
    get_vote_data,
    init_account_rewards,
    distribute,
    write_accounts_and_distribution,
    write_governance_stats,
)
from reporter.voters import parse_votes, get_voters
from reporter.queries import get_stakers
from reporter.types import AccountState, Config, Delegate, Account, Vote, Staker


@dataclass
class MockResponse:
    res: dict[str, Any]

    def json(self):
        return self.res


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


def test_get_stakers(monkeypatch, config):
    init_mocks(monkeypatch)

    stakers = get_stakers(config)

    assert all(to_checksum_address(s.id) == s.id for s in stakers)


def test_get_voters(monkeypatch, config):
    with open("reporter/test/stubs/snapshot-votes.json") as j:
        mock_votes = json.load(j)

    monkeypatch.setattr("reporter.voters.get_votes", lambda _: mock_votes)

    voters = parse_votes(config)
    assert len(voters) == len(mock_votes)


def test_get_voters_and_non_voters():

    path = "reporter/test/stubs/votes"

    with open(f"{path}/stakers.json") as j:
        mock_stakers = json.load(j)

    with open(f"{path}/votes.json") as j:
        mock_votes = json.load(j)

    with open(f"{path}/delegates.json") as j:
        mock_delegates = json.load(j)

    non_voter = "0x002b5dfb3c71e1dc97a2e5a0a7f69f3e7b83f269"
    delegated_voter = "0xFbEA6F2B10e8Ee770F37Fff9B8C9E10d9B65741D"
    delegated_non_voter = "0xea9f2e31ad16636f4e1af0012db569900401248a"
    voters = [
        "0x3070f20f86fDa706Ac380F5060D256028a46eC29",
        "0x7d0a2547b23e5F91F448bD9D2ae994748Af2C1E3",
        "0x71cfAfC5F334527Fd65821C0CbA69F000ad14F07",
        "0xe5cD86ff7f825a0ff6f699828D5c9bf163C0e3F9",
        "0x6593f0DC654597A5Bf2f78224FEEF81a545C1222",
        "0x657340f8F3187bB251700edE07140aaA93C08c35",
    ]

    votes = parse_obj_as(list[Vote], mock_votes)
    stakers = parse_obj_as(list[Staker], mock_stakers)
    delegates = parse_obj_as(list[Delegate], mock_delegates)

    (voted, non_voted) = get_voters(votes, stakers, delegates)

    assert set(voted) == set(voters + [delegated_voter])
    assert set(non_voted) == set(
        [to_checksum_address(v) for v in [non_voter, delegated_non_voter]]
    )


def test_get_vote_data(config, monkeypatch):

    init_mocks(monkeypatch)
    stakers = get_stakers(config)
    (votes, proposals, voters, non_voters) = get_vote_data(config, stakers)
    voter_ids = [v.voter for v in votes]

    assert len(proposals) == 4
    assert len(voters) + len(non_voters) == len(stakers)
    assert all(voter in voter_ids for voter in voters)


def test_init_accounts(config, monkeypatch):

    init_mocks(monkeypatch)
    stakers = get_stakers(config)
    (_, __, voters, non_voters) = get_vote_data(config, stakers)
    accounts = init_account_rewards(stakers, voters, config)

    slashed = [a for a in accounts if a.state == AccountState.SLASHED]
    active = [a for a in accounts if a.state == AccountState.ACTIVE]

    assert len(non_voters) == len(slashed)
    assert len(voters) == len(active)

    assert all(a.address in voters for a in active)
    assert not any(s.address in voters for s in slashed)

    assert all(s.address in non_voters for s in slashed)
    assert not any(a.address in non_voters for a in active)


def test_compute_distribution(config: Config, monkeypatch):
    init_mocks(monkeypatch)
    stakers = get_stakers(config)
    (_, __, voters, ___) = get_vote_data(config, stakers)
    accounts = init_account_rewards(stakers, voters, config)

    (distribution, reward_summaries, _) = distribute(config, accounts)
    total_rewards = Decimal(config.rewards.amount)
    aggregated_rewards = sum_totals(distribution)

    diff = aggregated_rewards - total_rewards

    # 0.0001% of total is lost to rounding error
    # this is $1 per $1_000_000 across all users
    assert diff < total_rewards * Decimal(0.000001)

    assert no_slashed_has_rewards(distribution)
    assert all_active_have_rewards(distribution)

    json.dumps(reward_summaries.dict(), indent=4)


def test_build(config: Config, monkeypatch):
    getcontext().prec = 42

    db = utils.get_db("reporter/test/stubs/db", drop=True)

    start_date = datetime.date.fromtimestamp(config.start_timestamp)
    end_date = datetime.date.fromtimestamp(config.end_timestamp)
    print(f"⚗ Building database from {start_date} to {end_date}...")

    init_mocks(monkeypatch)
    stakers = get_stakers(config)
    (votes, proposals, voters, non_voters) = get_vote_data(config, stakers)
    accounts = init_account_rewards(stakers, voters, config)
    (distribution, reward_summaries, stats) = distribute(config, accounts)
    print(stats)
    write_accounts_and_distribution(db, accounts, distribution)
    write_governance_stats(
        db, stakers, votes, proposals, voters, non_voters, reward_summaries, stats
    )


def no_slashed_has_rewards(distribution: list[Account]) -> bool:
    slashed = utils.filter_state(distribution, AccountState.SLASHED)
    return all(int(s.rewards) == 0 for s in slashed)


def all_active_have_rewards(distribution: list[Account]) -> bool:
    slashed = utils.filter_state(distribution, AccountState.ACTIVE)
    return all(int(s.rewards) > 0 for s in slashed)


def sum_totals(distribution: list[Account]) -> Decimal:
    account_rewards = [a.rewards for a in distribution]
    return functools.reduce(
        lambda acc, curr: acc + Decimal(curr), account_rewards, Decimal(0)
    )
