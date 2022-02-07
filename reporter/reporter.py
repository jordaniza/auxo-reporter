from tinydb import Query
from helpers import get_db, write_csv, write_list_csv, write_json
from account import AccountState

import json
import functools


Account = Query()


def report_governance(db, path):
    gov_stats = db.table("governance_stats").all()[0]

    stakers_fields = gov_stats["stakers"][0].keys()
    write_json(gov_stats["stakers"], f"{path}/json/stakers.json")
    write_csv(gov_stats["stakers"], f"{path}/csv/stakers.csv", stakers_fields)

    votes_fields = gov_stats["votes"][0].keys()
    write_csv(gov_stats["votes"], f"{path}/csv/votes.csv", votes_fields)

    proposals_fields = gov_stats["proposals"][0].keys()
    write_csv(gov_stats["proposals"], f"{path}/csv/proposals.csv", proposals_fields)

    write_list_csv(gov_stats["voters"], f"{path}/csv/voters.csv", "address")
    write_list_csv(gov_stats["non_voters"], f"{path}/csv/non_voters.csv", "address")


def report_rewards(db, path):
    distribution = db.table("distribution").all()

    distribution_fields = distribution[0].keys()
    write_json(distribution, f"{path}/json/distribution.json")
    write_csv(distribution, f"{path}/csv/distribution.csv", distribution_fields)

    accounts = db.table("accounts").all()
    rewards = [{"address": a["address"], "amount": a["slice_amount"]} for a in accounts]

    write_csv(rewards, f"{path}/csv/rewards.csv", ["address", "amount"])
    write_json(rewards, f"{path}/json/rewards.json")

def report_slashed(db, db_prev, path):
    accounts = db.table("accounts").search(Account.state == AccountState.SLASHED.value)
    accounts_prev = db_prev.table("accounts").search(Account.address.test(lambda addr: addr in [a["address"] for a in accounts]))

    slashed_accounts = [{"address": a["address"], "slice_amount": a["slice_amount"]} for a in accounts_prev]

    write_csv(slashed_accounts, f"{path}/csv/slashed.csv", ["address", "slice_amount"])
    write_json(slashed_accounts, f"{path}/json/slashed.json")

def build_claims(conf, db, path):
    accounts = db.table("accounts").search(Account.state == AccountState.ACTIVE.value)
    distributed = functools.reduce(lambda acc, a: acc + a["slice_amount"], accounts, 0)

    reward_window = {
        "chainId": 1,
        "rewardToken": "0x1083D743A1E53805a95249fEf7310D75029f7Cd6",
        "windowIndex": conf["distribution_window"],
        "totalRewardsDistributed": str(distributed),
        "recipients": {
            a["address"]: {
                "amount": str(a["slice_amount"]),
                "metaData": {
                    "reason": [f'Distribution for epoch {conf["distribution_window"]}']
                },
            }
            for a in accounts
        },
    }

    write_json(reward_window, f"{path}/claims.json")


def report(path, prev_path):
    conf = json.load(open(f"{path}/epoch-conf.json"))
    db = get_db(path)
    db_prev = get_db(prev_path)

    build_claims(conf, db, path)
    report_rewards(db, path)
    report_governance(db, path)
    report_slashed(db, db_prev, path)
