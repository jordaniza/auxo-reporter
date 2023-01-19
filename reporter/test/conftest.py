import json
import os
from dataclasses import dataclass
from decimal import getcontext
from typing import Any

import pytest

from reporter.conf_generator import load_conf
from reporter.models import Config

getcontext().prec = 45


@pytest.fixture
def config() -> Config:
    return load_conf("reporter/test/stubs/config")


@dataclass
class MockResponse:
    res: dict[str, Any]

    def json(self):
        return self.res


LIVE_CALLS_DISABLED = os.environ.get("PYTEST_LIVE_CALLS_ENABLED") != "TRUE"
SKIP_REASON = (
    "API Calls disabled: set PYTEST_LIVE_CALLS_ENABLED=TRUE in .env to run this test"
)


def mock_token_holders(monkeypatch, stub: str) -> None:
    with open(stub) as j:
        mock_holders = json.load(j)

    monkeypatch.setattr(
        "reporter.queries.graphql_iterate_query",
        lambda url, accessor, json: mock_holders["data"]["erc20Contract"]["balances"],
    )
