import pytest
from pydantic import ValidationError

from reporter.conf_generator import parse_rewards


def test_can_read_multiple_tokens_from_file(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "reporter/test/stubs/rewards.json")
    rewards = parse_rewards()
    assert len(rewards) == 2


@pytest.mark.parametrize(
    "invalids", [f"reporter/test/stubs/invalid_{i}.json" for i in range(1, 4)]
)
def test_invalid_json_fails(monkeypatch, invalids):
    monkeypatch.setattr("builtins.input", lambda _: invalids)
    with pytest.raises(ValidationError):
        parse_rewards()
