import pytest
import os, json
from pprint import pprint

from reporter.queries import (
    get_on_chain_votes,
    to_proposal,
    on_chain_votes_to_votes,
    get_token_holders,
)
from reporter.types import Config
from conftest import MockResponse


LIVE_CALLS_DISABLED = os.environ.get("PYTEST_LIVE_CALLS_ENABLED") != "TRUE"
SKIP_REASON = (
    "API Calls disabled: set PYTEST_LIVE_CALLS_ENABLED=TRUE in .env to run this test"
)


def mock_votes(monkeypatch):
    with open("reporter/test/stubs/votes/onchain-votes.json") as j:
        mock_on_chain_votes = json.load(j)

    monkeypatch.setattr(
        "reporter.queries.graphql_iterate_query",
        lambda url, accessor, json: mock_on_chain_votes["data"]["voteCasts"],
    )


@pytest.mark.skipif(LIVE_CALLS_DISABLED, reason=SKIP_REASON)
def test_should_have_data(config: Config):
    config.start_timestamp = 1668781800 - 100
    config.end_timestamp = 1668781800 + 100
    votes = get_on_chain_votes(config)

    assert len(votes) == 1


@pytest.mark.skipif(LIVE_CALLS_DISABLED, reason=SKIP_REASON)
def test_should_not_have_data(config: Config):
    config.start_timestamp = 0
    config.end_timestamp = 1000
    votes = get_on_chain_votes(config)

    assert len(votes) == 0


def test_parse_proposal(monkeypatch, config):
    mock_votes(monkeypatch)
    votes = get_on_chain_votes(config)
    v = on_chain_votes_to_votes(votes)
    p = to_proposal(votes[0]["proposal"])

    pprint([_v.dict() for _v in v], indent=4)
    pprint(p.dict(), indent=4)


def test_get_tokens():
    votes = get_token_holders()
    pprint(votes, indent=4)
