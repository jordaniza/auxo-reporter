import pytest, json
from reporter.xAuxo.rewards import (
    RedistributionWeight,
    RedistributionOption,
    compute_allocations,
    compute_xauxo_rewards,
    load_redistributions,
    ERROR_MESSAGES,
    NormalizedRedistributionWeight,
    compute_token_stats,
)
from reporter.rewards import (
    write_accounts_and_distribution,
    write_veauxo_stats,
    compute_rewards,
)
from reporter.queries import xauxo_accounts, get_x_auxo_statuses, get_xauxo_hodlers
from pydantic import ValidationError
from reporter.test.conftest import mock_token_holders
from pprint import pprint
from reporter.writer import build_claims
from decimal import Decimal
from reporter.errors import BadConfigException
from reporter.types import AccountState, Config, ERC20Metadata
from reporter.conf_generator import X_AUXO_HAIRCUT_PERCENT, XAUXO_ADDRESS
from reporter.test.conftest import LIVE_CALLS_DISABLED, SKIP_REASON
from reporter import utils
from copy import deepcopy


def test_require_address_for_transfer():
    with pytest.raises(ValidationError):
        RedistributionWeight(
            weight=1, address=None, option=RedistributionOption.TRANSFER
        )


def test_do_not_require_address_for_redistribute():
    r1 = RedistributionWeight(
        weight=1, address=None, option=RedistributionOption.REDISTRIBUTE_XAUXO
    )

    r2 = RedistributionWeight(
        weight=1, address=None, option=RedistributionOption.REDISTRIBUTE_VEAUXO
    )

    assert not r1.address
    assert not r2.address


def mock_ve_auxo_holders(monkeypatch) -> None:
    return mock_token_holders(monkeypatch, "reporter/test/stubs/tokens/veauxo.json")


@pytest.mark.skipif(LIVE_CALLS_DISABLED, reason=SKIP_REASON)
def test_compute_allocations(monkeypatch, config):
    mock_ve_auxo_holders(monkeypatch)

    holders = get_xauxo_hodlers(config)
    active = get_x_auxo_statuses(holders)
    accounts_in = xauxo_accounts(holders, active)

    (stats, rewards, haircut, accounts_out) = compute_allocations(accounts_in)

    pprint(f"{stats=}\n~{int(stats.active) / int(stats.total):.2f}% Active")
    pprint(rewards, indent=4)
    pprint(haircut, indent=4)
    pprint([a.dict() for a in accounts_out], indent=4)

    assert Decimal(stats.total) * Decimal(X_AUXO_HAIRCUT_PERCENT) == haircut
    assert Decimal(stats.total) * Decimal(1 - X_AUXO_HAIRCUT_PERCENT) == Decimal(
        rewards.amount
    )
    assert all(
        int(a.rewards) == 0 for a in accounts_out if a.state == AccountState.INACTIVE
    )
    assert all(
        int(a.rewards) > 0 for a in accounts_out if a.state == AccountState.ACTIVE
    )


@pytest.mark.parametrize(
    "filenum, err",
    [
        (1, ERROR_MESSAGES.DUPLICATE_XAUXO),
        (2, ERROR_MESSAGES.DUPLICATE_TRANSFER),
        (3, ERROR_MESSAGES.VEAUXO_NOT_IMPLEMENTED),
    ],
)
def test_load_redistributions_invalid(filenum: int, err: str):
    path = f"reporter/test/stubs/config/redistributions_invalid_{filenum}.json"
    with pytest.raises(BadConfigException) as E:
        load_redistributions(path)
    assert E.value.args[0] == err


def test_load_redistributions_valid():
    path = "reporter/test/stubs/config/redistributions.json"
    dist = load_redistributions(path)
    assert len(dist) == 4


def assertAlmostEq(a: int, b: int, delta: float):
    assert abs(a - b) <= delta


def test_compute_redistributions(monkeypatch, config: Config):
    mock_ve_auxo_holders(monkeypatch)

    holders = get_xauxo_hodlers(config)
    active = get_x_auxo_statuses(holders)
    accounts_in = xauxo_accounts(holders, active)

    dist = load_redistributions("reporter/test/stubs/config/redistributions.json")
    xauxo_stats, accounts, redistributions, stakers_rewards = compute_allocations(
        accounts_in, config.rewards, dist
    )

    reward = deepcopy(config.rewards)
    reward.amount = str(int(stakers_rewards))

    distribution_rewards = compute_rewards(
        reward,
        Decimal(xauxo_stats.active),
        accounts,
    )

    pprint(distribution_rewards.dict(), indent=4)

    # printing and assertions
    _print_eth_redistributions(redistributions)
    print(int(stakers_rewards) / 10**18)
    _assert_stakers_rewards_reconcile(redistributions, config, int(stakers_rewards))
    print(json.dumps([a.dict() for a in accounts], indent=4))
    # END printing and assertions

    # write the data
    db = utils.get_db("reporter/test/stubs/db", drop=False)

    write_accounts_and_distribution(db, accounts, accounts, "xAUXO")
    build_claims(config, db, "reporter/test/stubs/db", "xAUXO")


def _print_eth_redistributions(redistributions: list[NormalizedRedistributionWeight]):
    redistributions_with_eth = [
        {"eth_value": int(r.rewards) / 10**18, **r.dict()} for r in redistributions
    ]

    print(json.dumps(redistributions_with_eth, indent=4))


def _assert_stakers_rewards_reconcile(
    redistributions: list[NormalizedRedistributionWeight],
    config: Config,
    stakers_rewards: int,
):
    rewards_to_non_stakers = sum(
        int(r.rewards)
        for r in redistributions
        if r.option != RedistributionOption.REDISTRIBUTE_XAUXO
    )
    net_rewards_to_stakers = int(config.rewards.amount) - rewards_to_non_stakers

    ONE_TEN_MILLIONTH = 0.00000001
    max_delta = int(config.rewards.amount) * ONE_TEN_MILLIONTH

    assertAlmostEq(
        stakers_rewards,
        net_rewards_to_stakers,
        max_delta,
    )
