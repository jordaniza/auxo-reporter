import json
import pytest
from unittest.mock import Mock
from reporter.errors import *
from reporter.models import Config, OffChainVote
from reporter.queries import graphql_iterate_query, extract_nested_graphql
from reporter.test.conftest import (
    LIVE_CALLS_DISABLED,
    SKIP_REASON,
    mock_token_holders,
)
from reporter.queries.voters import (
    combine_on_off_chain_votes,
    parse_onchain_votes,
    parse_offchain_votes,
    get_onchain_votes,
)


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
        "reporter.queries.voters.get_onchain_votes",
        lambda conf: mock_on_chain_votes["data"]["voteCasts"],
    )


def mock_get_off_chain_votes(monkeypatch) -> None:
    with open("reporter/test/stubs/votes/votes.json") as j:
        mock_votes = json.load(j)

    monkeypatch.setattr(
        "reporter.queries.voters.get_offchain_votes",
        lambda conf: mock_votes,
    )


def mock_votes_both(monkeypatch) -> None:
    mock_get_on_chain_votes(monkeypatch)
    mock_get_off_chain_votes(monkeypatch)


def mock_ve_auxo_holders(monkeypatch) -> None:
    return mock_token_holders(monkeypatch, "reporter/test/stubs/tokens/arv.json")


def mock_x_auxo_holders(monkeypatch) -> None:
    return mock_token_holders(monkeypatch, "reporter/test/stubs/tokens/xauxo.json")


def test_extract_nested_graphql():
    # Test case 1: Basic test with valid access path
    response = {"data": {"foo": {"bar": 42}}}
    access_path = ["foo", "bar"]
    assert extract_nested_graphql(response, access_path) == 42

    # Test case 2: Test with invalid access path
    response = {"data": {"foo": {"bar": 42}}}
    access_path = ["foo", "baz"]
    with pytest.raises(KeyError):
        extract_nested_graphql(response, access_path)

    # Test case 3: Test with empty access path
    response = {"data": {"foo": {"bar": 42}}}
    access_path = []
    assert extract_nested_graphql(response, access_path) == {"foo": {"bar": 42}}

    # Test case 4: Test with response object that does not contain 'data' key
    response = {"foo": {"bar": 42}}
    access_path = ["foo", "bar"]
    with pytest.raises(KeyError):
        extract_nested_graphql(response, access_path)


def test_graphql_iterate_query_empty_response(monkeypatch):
    mock_response = None
    mock_json = Mock(return_value=mock_response)
    requests_post_mock = Mock(return_value=Mock(json=mock_json))

    url = "https://graphql.example.com"
    access_path = ["users", "edges", "node", "id"]
    params = {"query": "query {}"}

    monkeypatch.setattr(
        "reporter.queries.requests.post",
        requests_post_mock,
    )

    with pytest.raises(EmptyQueryError):
        graphql_iterate_query(url, access_path, params, max_loops=5)


def test_graphql_iterate_query_error_response(monkeypatch):
    mock_response = {"errors": [{"message": "An error occurred"}]}
    mock_json = Mock(return_value=mock_response)
    requests_post_mock = Mock(return_value=Mock(json=mock_json))

    url = "https://graphql.example.com"
    access_path = ["users", "edges", "node", "id"]
    params = {"query": "query {}"}

    monkeypatch.setattr(
        "reporter.queries.requests.post",
        requests_post_mock,
    )
    with pytest.raises(EmptyQueryError):
        graphql_iterate_query(url, access_path, params)


def test_graphql_iterate_query_too_many_loops(monkeypatch):
    mock_response = {
        "data": {
            "users": {
                "edges": {
                    "nodes": [
                        {"id": "1"},
                        {"id": "2"},
                        {"id": "3"},
                    ]
                }
            }
        }
    }
    mock_json = Mock(return_value=mock_response)
    requests_post_mock = Mock(return_value=Mock(json=mock_json))

    url = "https://graphql.example.com"
    access_path = ["users", "edges", "nodes"]
    params = {"query": "query {}", "variables": {"skip": 1}}

    monkeypatch.setattr(
        "reporter.queries.requests.post",
        requests_post_mock,
    )
    with pytest.raises(TooManyLoopsError):
        graphql_iterate_query(url, access_path, params, max_loops=3)


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
    with open("reporter/test/stubs/votes/onchain-votes.json") as j:
        votes = json.load(j)

    v = parse_onchain_votes(config)
    proposal = v[0].proposal

    assert proposal.id == votes["data"]["voteCasts"][0]["proposal"]["id"]


def test_can_combine_votes(monkeypatch, config):
    mock_votes_both(monkeypatch)

    mock_off_chain_votes = parse_offchain_votes(config)
    mock_on_chain_votes = parse_onchain_votes(config)

    combined = combine_on_off_chain_votes(mock_off_chain_votes, mock_on_chain_votes)

    assert len(mock_on_chain_votes) > 0
    assert len(mock_off_chain_votes) > 0
    assert len(combined) == len(mock_off_chain_votes) + len(mock_on_chain_votes)
    assert all(isinstance(c, OffChainVote) for c in combined)
