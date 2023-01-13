import pytest
from dataclasses import dataclass
from typing import Any
from reporter.types import Config
from reporter.conf_generator import load_conf


@pytest.fixture
def config() -> Config:
    return load_conf("reporter/test/stubs/config")


@dataclass
class MockResponse:
    res: dict[str, Any]

    def json(self):
        return self.res
