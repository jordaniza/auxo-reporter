import pytest
from reporter.types import Config
from reporter.conf_generator import load_conf


@pytest.fixture
def config() -> Config:
    return load_conf("reporter/test/stubs/config")
