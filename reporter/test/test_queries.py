import json
import os
from pprint import pprint

import pytest

from reporter.models import Config, Vote
from reporter.queries import (
    get_onchain_votes,
    get_veauxo_stakers,
    get_x_auxo_statuses,
    get_xauxo_stakers,
    to_proposal,
    xauxo_accounts,
)
from reporter.test.conftest import (
    LIVE_CALLS_DISABLED,
    SKIP_REASON,
    MockResponse,
    mock_token_holders,
)
from reporter.voters import (
    combine_on_off_chain_votes,
    parse_on_chain_votes,
    parse_votes,
)


def mock_ve_auxo_holders(monkeypatch) -> None:
    return mock_token_holders(monkeypatch, "reporter/test/stubs/tokens/veauxo.json")


def mock_x_auxo_holders(monkeypatch) -> None:
    return mock_token_holders(monkeypatch, "reporter/test/stubs/tokens/xauxo.json")


def mock_votes(monkeypatch) -> None:
    with open("reporter/test/stubs/votes/onchain-votes.json") as j:
        mock_on_chain_votes = json.load(j)

    monkeypatch.setattr(
        "reporter.queries.graphql_iterate_query",
        lambda url, accessor, json: mock_on_chain_votes["data"]["voteCasts"],
    )


def mock_get_on_chain_votes(monkeypatch) -> None:
    with open("reporter/test/stubs/votes/onchain-votes.json") as j:
        mock_on_chain_votes = json.load(j)

    monkeypatch.setattr(
        "reporter.voters.get_on_chain_votes",
        lambda conf: mock_on_chain_votes["data"]["voteCasts"],
    )


def mock_get_off_chain_votes(monkeypatch) -> None:
    with open("reporter/test/stubs/votes/votes.json") as j:
        mock_votes = json.load(j)

    monkeypatch.setattr(
        "reporter.voters.get_votes",
        lambda conf: mock_votes,
    )


def mock_votes_both(monkeypatch) -> None:
    mock_get_on_chain_votes(monkeypatch)
    mock_get_off_chain_votes(monkeypatch)


@pytest.mark.skipif(LIVE_CALLS_DISABLED, reason=SKIP_REASON)
def test_should_have_data(config: Config):
    config.start_timestamp = 1668781800 - 100
    config.end_timestamp = 1668781800 + 100
    votes = get_onchain_votes(config)

    assert len(votes) == 1


@pytest.mark.skipif(LIVE_CALLS_DISABLED, reason=SKIP_REASON)
def test_should_not_have_data(config: Config):
    config.start_timestamp = 0
    config.end_timestamp = 1000
    votes = get_onchain_votes(config)

    assert len(votes) == 0


def test_parse_proposal(monkeypatch, config):
    mock_votes_both(monkeypatch)
    votes = get_onchain_votes(config)
    v = parse_on_chain_votes(votes)
    p = to_proposal(votes[0]["proposal"])

    pprint([_v.dict() for _v in v], indent=4)
    pprint(p.dict(), indent=4)


def test_get_tokens(monkeypatch, config: Config):
    mock_ve_auxo_holders(monkeypatch)
    mock_x_auxo_holders(monkeypatch)

    config.block_snapshot = 8320117

    xauxo = get_xauxo_stakers(config)
    pprint(xauxo, indent=4)

    veauxo = get_veauxo_stakers(config)
    pprint(veauxo, indent=4)

    active = get_x_auxo_statuses(veauxo)

    pprint(active, indent=4)

    accs = xauxo_accounts(veauxo, active, config)
    pprint(accs, indent=4)


def test_can_combine_votes(monkeypatch, config):
    mock_votes_both(monkeypatch)

    mock_off_chain_votes = parse_votes(config)
    mock_on_chain_votes = parse_on_chain_votes(config)

    combined = combine_on_off_chain_votes(mock_off_chain_votes, mock_on_chain_votes)

    assert len(mock_on_chain_votes) > 0
    assert len(mock_off_chain_votes) > 0
    assert len(combined) == len(mock_off_chain_votes) + len(mock_on_chain_votes)
    assert all(isinstance(c, Vote) for c in combined)
