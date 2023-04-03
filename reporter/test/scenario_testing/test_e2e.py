"""
This is a scenario test using deterministic data to test the rewards distribution process.

Our input is the input file, we're going to load it with the following settings:

Scenario 1: Easy numbers

Distribute 1000 WETH to ARV and PRV holders

Expect 700 WETH to be distributed to ARV holders
Expect 300 WETH to be distributed to PRV holders

We have 5 ARV holders, each with 1000 AUXO locked
- 3 holders are active
- 2 holders are inactive


We have 4 PRV holders each with 1000 PRV
- 3 PRV holders are staked
- 1 PRV holder is not staked

We have 1 multisig who is not a PRV holder
- he will receive 100% of the redistributions

Scenario 2: Same but with ARV decay

Scenario 3: Same but with PRV redistributions

"""
import json
import pytest

from reporter import config
from reporter.run_arv import run_arv as arv_main
from reporter.run_prv import run_prv as prv_main
from reporter.test.scenario_testing.create_scenario import init_users


def read_mock(file_name, SCENARIO_NUMBER):
    with open(
        f"reporter/test/scenario_testing/{SCENARIO_NUMBER}/{file_name}", "r"
    ) as f:
        mock = json.load(f)
    return mock


def read_mock_0(file_name):
    return read_mock(file_name, 0)


def read_mock_1(file_name):
    return read_mock(file_name, 1)


def test_e2e_0(monkeypatch):
    generate_users = init_users(0)

    # path to the input file
    monkeypatch.setattr(
        "builtins.input",
        lambda *_: "./reporter/test/scenario_testing/inputs/scenario-1.json",
    )

    epoch = config.main()

    # get_token_hodlers
    monkeypatch.setattr(
        "reporter.queries.arv_stakers.get_token_hodlers",
        lambda *_: read_mock_0("mock_arv.json")["data"]["erc20Contract"]["balances"],
    )

    # get locks
    monkeypatch.setattr(
        "reporter.queries.arv_stakers.get_locks",
        lambda *_: read_mock_0("arv_locks.json"),
    )

    # get_boosted_lock
    monkeypatch.setattr(
        "reporter.queries.arv_stakers.get_boosted_lock",
        lambda *_: read_mock_0("arv_boosted.json"),
    )

    # get_offchain_votes
    monkeypatch.setattr(
        "reporter.queries.voters.get_offchain_votes",
        lambda *_: read_mock_0("votes_off.json"),
    )

    # get_onchain_votes
    monkeypatch.setattr(
        "reporter.queries.voters.get_onchain_votes",
        lambda *_: read_mock_0("votes_on.json")["data"]["voteCasts"],
    )

    # filter proposals?
    monkeypatch.setattr("builtins.input", lambda _: "N")

    # run ARV
    arv_main(epoch)

    """
    Now we can run some checks:
    - The total distributed to holders equals the total ARV rewards
    - The inactive voters didn't get anything
    - The active voters got the correct amount
    - Number of voters and non-voters is correct
    """

    with open(f"{epoch}/claims-ARV.json", "r") as f:
        claims_arv = json.load(f)

    recipients = claims_arv["recipients"]
    total_distributed = sum([int(c["rewards"]) for c in recipients.values()])
    distributed_addresses = [c for c in recipients.keys()]

    assert abs(total_distributed - int(claims_arv["aggregateRewards"]["amount"])) <= 1
    assert all(
        u.address in distributed_addresses for u in generate_users if u.is_active
    )
    assert not any(
        u.address in distributed_addresses for u in generate_users if not u.is_active
    )

    # get_prv_total_supply
    monkeypatch.setattr(
        "reporter.run_prv.get_prv_total_supply",
        lambda *_: sum(int(u.PRV_amount) for u in generate_users),
    )

    # get_all_prv_depositors
    monkeypatch.setattr(
        "reporter.queries.prv_stakers.get_all_prv_depositors",
        lambda *_: read_mock_0("prv_depositeds.json")["data"]["depositeds"],
    )

    # ger_prv_staked_balances
    monkeypatch.setattr(
        "reporter.queries.prv_stakers.get_prv_staked_balances",
        lambda *_: read_mock_0("prv_stakes.json"),
    )

    # run PRV
    prv_main(epoch)

    """
    Additional PRV Checks
    - The total distributed to holders equals the total PRV rewards
    - The non-stakers didn't get anything
    - The stakers got the correct amount
    - redistributions happened correctly
    """

    with open(f"{epoch}/claims-PRV.json", "r") as f:
        claims_prv = json.load(f)

    prv_recipients = claims_prv["recipients"]
    total_distributed_prv = sum([int(c["rewards"]) for c in prv_recipients.values()])
    distributed_addresses_prv = [c for c in prv_recipients.keys()]

    assert (
        abs(total_distributed_prv - int(claims_prv["aggregateRewards"]["amount"])) <= 1
    )
    assert all(
        u.address in distributed_addresses_prv for u in generate_users if u.staked_PRV
    )
    assert not any(
        u.address in distributed_addresses_prv
        for u in generate_users
        if not u.staked_PRV
    )


def test_e2e_1(monkeypatch):
    generate_users = init_users(1)

    # path to the input file
    monkeypatch.setattr(
        "builtins.input",
        lambda *_: "./reporter/test/scenario_testing/inputs/scenario-2.json",
    )

    epoch = config.main()

    # get_token_hodlers
    monkeypatch.setattr(
        "reporter.queries.arv_stakers.get_token_hodlers",
        lambda *_: read_mock_1("mock_arv.json")["data"]["erc20Contract"]["balances"],
    )

    # get locks
    monkeypatch.setattr(
        "reporter.queries.arv_stakers.get_locks",
        lambda *_: read_mock_1("arv_locks.json"),
    )

    # get_boosted_lock
    monkeypatch.setattr(
        "reporter.queries.arv_stakers.get_boosted_lock",
        lambda *_: read_mock_1("arv_boosted.json"),
    )

    # get_offchain_votes
    monkeypatch.setattr(
        "reporter.queries.voters.get_offchain_votes",
        lambda *_: read_mock_1("votes_off.json"),
    )

    # get_onchain_votes
    monkeypatch.setattr(
        "reporter.queries.voters.get_onchain_votes",
        lambda *_: read_mock_1("votes_on.json")["data"]["voteCasts"],
    )

    # filter proposals?
    monkeypatch.setattr("builtins.input", lambda _: "N")

    # run ARV
    arv_main(epoch)

    """
    Now we can run some checks:
    - The total distributed to holders equals the total ARV rewards
    - The inactive voters didn't get anything
    - The active voters got the correct amount
    - Number of voters and non-voters is correct
    """

    with open(f"{epoch}/claims-ARV.json", "r") as f:
        claims_arv = json.load(f)

    recipients = claims_arv["recipients"]
    total_distributed = sum([int(c["rewards"]) for c in recipients.values()])
    distributed_addresses = [c for c in recipients.keys()]

    assert abs(total_distributed - int(claims_arv["aggregateRewards"]["amount"])) <= 1
    assert all(
        u.address in distributed_addresses for u in generate_users if u.is_active
    )
    assert not any(
        u.address in distributed_addresses for u in generate_users if not u.is_active
    )

    # get_prv_total_supply
    monkeypatch.setattr(
        "reporter.run_prv.get_prv_total_supply",
        lambda *_: sum(int(u.PRV_amount) for u in generate_users),
    )

    # get_all_prv_depositors
    monkeypatch.setattr(
        "reporter.queries.prv_stakers.get_all_prv_depositors",
        lambda *_: read_mock_1("prv_depositeds.json")["data"]["depositeds"],
    )

    # ger_prv_staked_balances
    monkeypatch.setattr(
        "reporter.queries.prv_stakers.get_prv_staked_balances",
        lambda *_: read_mock_1("prv_stakes.json"),
    )

    # run PRV
    prv_main(epoch)

    """
    Additional PRV Checks
    - The total distributed to holders equals the total PRV rewards
    - The non-stakers didn't get anything
    - The stakers got the correct amount
    - redistributions happened correctly
    """

    with open(f"{epoch}/claims-PRV.json", "r") as f:
        claims_prv = json.load(f)

    prv_recipients = claims_prv["recipients"]
    total_distributed_prv = sum([int(c["rewards"]) for c in prv_recipients.values()])
    distributed_addresses_prv = [c for c in prv_recipients.keys()]

    assert (
        abs(total_distributed_prv - int(claims_prv["aggregateRewards"]["amount"])) <= 1
    )
    assert all(
        u.address in distributed_addresses_prv for u in generate_users if u.staked_PRV
    )
    assert not any(
        u.address in distributed_addresses_prv
        for u in generate_users
        if not u.staked_PRV
    )
