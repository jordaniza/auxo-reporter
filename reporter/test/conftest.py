import pytest
from pydantic import parse_file_as
from reporter.types import Config


@pytest.fixture
def config() -> Config:
    return parse_file_as(Config, "reporter/test/stubs/config/epoch-conf.json")
