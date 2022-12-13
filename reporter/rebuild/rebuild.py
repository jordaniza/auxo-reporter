import os, sys

currentdir = os.path.dirname(os.path.realpath(__file__))
parentdir = os.path.dirname(currentdir)
sys.path.append(parentdir)


from tinydb import TinyDB
from pathlib import Path
from eth_utils import to_checksum_address
from reporter.account import to_staker

import csv
import json
import itertools


def read_csv(reader):
    for r in reader:
        if reader.line_num == 1:
            continue
        yield r


def read_stakers(f):
    reader = csv.DictReader(open(f, "r"), fieldnames=["address", "amount"])

    return [
        (to_checksum_address(staker["address"]), int(staker["amount"]))
        for staker in read_csv(reader)
    ]


def read_amounts_for_active(f, inactive):
    reader = csv.DictReader(open(f, "r"), fieldnames=["address", "amount"])

    return [
        (to_checksum_address(amt["address"]), int(amt["amount"]))
        for amt in read_csv(reader)
        if to_checksum_address(amt["address"]) not in inactive
    ]


def read_gov_stats(path):
    votes_fields = ["voter", "choice", "proposal", "created"]
    votes_reader = csv.DictReader(open(f"{path}/votes.csv"), votes_fields)
    votes = [v for v in read_csv(votes_reader)]

    proposals_fields = ["id", "title", "author", "choices", "created", "start", "end"]
    proposals_reader = csv.DictReader(open(f"{path}/proposals.csv"), proposals_fields)
    proposals = [p for p in read_csv(proposals_reader)]

    voters_fields = ["address"]
    voters_reader = csv.DictReader(open(f"{path}/voted.csv"), voters_fields)
    voters = [v["address"] for v in read_csv(voters_reader)]

    non_voters_fields = ["address"]
    non_voters_reader = csv.DictReader(open(f"{path}/not_voted.csv"), non_voters_fields)
    non_voters = [v["address"] for v in read_csv(non_voters_reader)]

    return (votes, proposals, voters, non_voters)


def get_active_account(active_staker, stakers):
    account = {}

    account["state"] = "active"
    account["inactive_windows"] = []
    account["address"] = active_staker[0]
    account["slice_amount"] = int(active_staker[1])
    account["vedough_balance"] = stakers[active_staker[0]]

    return account


def get_inactive_account(inactive_staker, stakers):
    account = {}

    account["state"] = "inactive"
    account["address"] = inactive_staker["address"]
    account["slice_amount"] = inactive_staker["amount"]
    account["vedough_balance"] = stakers[inactive_staker["address"]]
    account["inactive_windows"] = inactive_staker["inactive_windows"]

    return account


def get_distribution(path):
    distribution_fields = ["account", "amount"]
    distribution_reader = csv.DictReader(
        open(f"{path}/slice_amounts.csv"), distribution_fields
    )

    return [d for d in read_csv(distribution_reader)]


def write_governance_stats(db, stakers, votes, proposals, voters, non_voters):
    db.table("governance_stats").insert(
        {
            "stakers": list(map(to_staker, stakers)),
            "votes": votes,
            "proposals": proposals,
            "voters": voters,
            "non_voters": non_voters,
        },
    )


def rebuild():
    path = "./reports/2021-12"

    Path(path).mkdir(parents=True, exist_ok=True)
    Path(f"{path}/csv/").mkdir(parents=True, exist_ok=True)
    Path(f"{path}/json/").mkdir(parents=True, exist_ok=True)

    db = TinyDB(f"{path}/reporter-db.json")
    db.drop_tables()

    stakers = read_stakers("./reports/old_reports/staking/2021-12/stakers.csv")
    stakers_map = {addr: int(amount) for (addr, amount) in stakers}
    (votes, proposals, voters, non_voters) = read_gov_stats(
        "./reports/old_reports/staking/2021-12"
    )
    distribution = get_distribution("./reports/old_reports/staking/2021-12")

    inactive_stakers = json.load(open(("./reports/old_reports/epochs/3/inactive.json")))

    amounts_after_unclaimed = read_amounts_for_active(
        "./reports/old_reports/staking/2021-12/slice_amounts_after_unclaimed.csv",
        [item["address"] for item in inactive_stakers],
    )

    accounts = list(
        map(get_active_account, amounts_after_unclaimed, itertools.repeat(stakers_map))
    ) + list(map(get_inactive_account, inactive_stakers, itertools.repeat(stakers_map)))

    write_governance_stats(db, stakers, votes, proposals, voters, non_voters)

    db.table("accounts").insert_multiple(accounts)
    db.table("distribution").insert_multiple(distribution)


if __name__ == "__main__":
    rebuild()
