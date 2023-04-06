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

Expected outcomes:
- Total to ARV holders is 700 WETH
- This should be 700/3 = 233.33 WETH per active ARV holder
- Inactive holders should not be in claims


Scenario 2: Same but with ARV decay

500 WETH in total
60% to ARV = 300 WETH
Still all users have 1000 ARV, except 1 with 1500 ARV

1 ARV user who has 2/3 of rewards
1 ARV user who has 3/4 of rewards 
2 ARV user who has full rewards 

This should work out to:

https://docs.google.com/spreadsheets/d/1tsBOQC_kK8eBWlogCHK0dchqO26Ii7NyqGwoSOkb1wc/edit#gid=0

Meaning with

"""
import json
from typing import Callable

from reporter import config
from reporter.run_arv import run_arv as arv_main
from reporter.run_prv import run_prv as prv_main
from reporter.test.scenario_testing.create_scenario import init_users


def _read_mock(file_name, SCENARIO_NUMBER):
    with open(
        f"reporter/test/scenario_testing/{SCENARIO_NUMBER}/{file_name}", "r"
    ) as f:
        mock = json.load(f)
    return mock


def init_e2e_arv_mocks(monkeypatch, read_mock: Callable):
    # path to the input file
    # get_token_hodlers
    monkeypatch.setattr(
        "reporter.queries.arv_stakers.get_token_hodlers",
        lambda *_: read_mock("mock_arv.json")["data"]["erc20Contract"]["balances"],
    )

    # get locks
    monkeypatch.setattr(
        "reporter.queries.arv_stakers.get_locks",
        lambda *_: read_mock("arv_locks.json"),
    )

    # get_boosted_lock
    monkeypatch.setattr(
        "reporter.queries.arv_stakers.get_boosted_lock",
        lambda *_: read_mock("arv_boosted.json"),
    )

    # get_offchain_votes
    monkeypatch.setattr(
        "reporter.queries.voters.get_offchain_votes",
        lambda *_: read_mock("votes_off.json"),
    )

    # get_onchain_votes
    monkeypatch.setattr(
        "reporter.queries.voters.get_onchain_votes",
        lambda *_: read_mock("votes_on.json")["data"]["voteCasts"],
    )

    # filter proposals?
    monkeypatch.setattr("builtins.input", lambda _: "N")


def init_e2e_prv_mocks(monkeypatch, read_mock: Callable, generate_users):
    # get_prv_total_supply
    monkeypatch.setattr(
        "reporter.run_prv.get_prv_total_supply",
        lambda *_: sum(int(u.PRV_amount) for u in generate_users),
    )

    # get_all_prv_depositors
    monkeypatch.setattr(
        "reporter.queries.prv_stakers.get_all_prv_depositors",
        lambda *_: read_mock("prv_depositeds.json")["data"]["depositeds"],
    )

    # ger_prv_staked_balances
    monkeypatch.setattr(
        "reporter.queries.prv_stakers.get_prv_staked_balances",
        lambda *_: read_mock("prv_stakes.json"),
    )


def test_e2e_0(monkeypatch):
    scenario = 0
    generate_users = init_users(scenario)

    def read_mock(file_name):
        return _read_mock(file_name, scenario)

    # path to the input file
    monkeypatch.setattr(
        "builtins.input",
        lambda *_: f"./reporter/test/scenario_testing/inputs/scenario-{scenario}.json",
    )

    epoch = config.main()

    init_e2e_arv_mocks(monkeypatch, read_mock)

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

    with open(f"{epoch}/reporter-db.json", "r") as f:
        reporter_db_arv = json.load(f)

    recipients = claims_arv["recipients"]
    total_distributed = sum([int(c["rewards"]) for c in recipients.values()])
    distributed_addresses = [c for c in recipients.keys()]
    active_users = [u for u in generate_users if u.is_active]
    inactive_users = [u for u in generate_users if not u.is_active]

    # abs diff begween total distributed and total rewards is <= 1
    assert abs(total_distributed - int(claims_arv["aggregateRewards"]["amount"])) <= 1
    assert all(u.address in distributed_addresses for u in active_users)
    assert not any(u.address in distributed_addresses for u in inactive_users)

    stats = reporter_db_arv["ARV_stats"]["1"]["token_stats"]
    assert stats["active"] == "3000000000000000000000"
    assert stats["inactive"] == "2000000000000000000000"
    assert stats["total"] == "5000000000000000000000"

    # expect 233.33 WETH per active voter
    assert all(
        recipients[u.address]["rewards"] == "233333333333333333333"
        for u in active_users
    )

    init_e2e_prv_mocks(monkeypatch, read_mock, generate_users)
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
        abs(total_distributed_prv - int(claims_prv["aggregateRewards"]["amount"])) <= 2
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
    scenario = 1
    generate_users = init_users(scenario)

    def read_mock(file_name):
        return _read_mock(file_name, scenario)

    # path to the input file
    monkeypatch.setattr(
        "builtins.input",
        lambda *_: f"./reporter/test/scenario_testing/inputs/scenario-{scenario}.json",
    )

    epoch = config.main()

    init_e2e_arv_mocks(monkeypatch, read_mock)

    # run ARV
    arv_main(epoch)

    """
    Now we can run some checks:
    - The total distributed to holders equals the total ARV rewards
    - The inactive voters didn't get anything
    - The active voters got the correct amount
    - Number of voters and non-voters is correct
    1000 ARV @ 67% ~51.06382979 WETH
    1000 ARV @ 75% ~57.44680851 WETH
    1000 ARV ~76.59574468 WETH
    1500 ARV ~114.893617 WETH
    """

    with open(f"{epoch}/claims-ARV.json", "r") as f:
        claims_arv = json.load(f)

    recipients = claims_arv["recipients"]
    total_distributed = sum([int(c["rewards"]) for c in recipients.values()])
    distributed_addresses = [c for c in recipients.keys()]

    assert abs(total_distributed - int(claims_arv["aggregateRewards"]["amount"])) <= 2
    assert all(
        u.address in distributed_addresses for u in generate_users if u.is_active
    )
    assert not any(
        u.address in distributed_addresses for u in generate_users if not u.is_active
    )

    rewards = lambda i: recipients[generate_users[i].address]["rewards"]

    # these aren't exact but are close enough that we can attribute to rounding
    assert rewards(0) == "51063829787234039776"
    assert rewards(1) == "57446808510638298513"
    assert rewards(2) == "76595744680851064684"
    assert rewards(3) == "114893617021276597026"

    init_e2e_prv_mocks(monkeypatch, read_mock, generate_users)

    # run PRV
    prv_main(epoch)

    """
    Additional PRV Checks
    - The total distributed to holders equals the total PRV rewards
    - The non-stakers didn't get anything
    - The stakers got the correct amount
    - redistributions happened correctly

    We'd expect 200 WETH distributed as follows
    2 active PRV users and 1 inactive

    Each active PRV user gets 200/3 = 66.666666666
    The remaining 66 is split 50/50
    A transfer to the manual address of 33.33
    33.33 split 50/50 between the 2 active PRV users:

    Final totals:
    Active user 1: 66.666666666 + 33.33/2 = 83.33
    Active user 2: 66.666666666 + 33.33/2 = 83.33
    Inactive user: 0
    Manual address: 33.33
    Total distributed: 83.33 + 83.33 + 33.33 = 200

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

    with open(f"{epoch}/claims-PRV.json", "r") as f:
        claims_prv = json.load(f)

    recipients = claims_prv["recipients"]
    rewards = lambda i: recipients[generate_users[i].address]["rewards"]

    assert rewards(5) == "83333333333333333333"
    assert rewards(6) == "83333333333333333333"
    assert list(recipients.values())[-1]["rewards"] == "33333333333333333333"


def test_e2e_2(monkeypatch):
    scenario = 2
    generate_users = init_users(scenario)

    def read_mock(file_name):
        return _read_mock(file_name, scenario)

    # path to the input file
    monkeypatch.setattr(
        "builtins.input",
        lambda *_: f"./reporter/test/scenario_testing/inputs/scenario-{scenario}.json",
    )

    epoch = config.main()

    init_e2e_arv_mocks(monkeypatch, read_mock)

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

    with open(f"{epoch}/reporter-db.json", "r") as f:
        reporter_db_arv = json.load(f)

    recipients = claims_arv["recipients"]
    total_distributed = sum([int(c["rewards"]) for c in recipients.values()])
    distributed_addresses = [c for c in recipients.keys()]
    active_users = [u for u in generate_users if u.is_active]
    inactive_users = [u for u in generate_users if not u.is_active]

    # abs diff begween total distributed and total rewards is <= 1
    assert abs(total_distributed - int(claims_arv["aggregateRewards"]["amount"])) <= 1
    assert all(u.address in distributed_addresses for u in active_users)
    assert not any(u.address in distributed_addresses for u in inactive_users)

    stats = reporter_db_arv["ARV_stats"]["1"]["token_stats"]

    init_e2e_prv_mocks(monkeypatch, read_mock, generate_users)
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
        abs(total_distributed_prv - int(claims_prv["aggregateRewards"]["amount"])) <= 2
    )
    assert all(
        u.address in distributed_addresses_prv for u in generate_users if u.staked_PRV
    )
    assert not any(
        u.address in distributed_addresses_prv
        for u in generate_users
        if not u.staked_PRV
    )
