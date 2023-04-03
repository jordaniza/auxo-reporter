import json
import os
from dataclasses import dataclass
from decimal import getcontext
from typing import Any

import pytest

from reporter.config import load_conf
from reporter.models import Config

getcontext().prec = 45


@pytest.fixture
def config() -> Config:
    return load_conf("reporter/test/stubs/config")


@pytest.fixture()
def ADDRESSES():
    return [
        "0x9bc33f6155eFAcc290c3C50E9B5b24b668562732",
        "0xfDe38ad4bBbeC867e6cb4Bb31FbFB2074c959A83",
        "0x8BB4C0b502f869af3B25166930507a6E8c3038D4",
        "0x7Ac54A0406FA2B465E0D57C66597BE83A4b149fC",
        "0xdeA708968f8dd520f5e2F0aB6785F28c98521ca8",
    ]


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
