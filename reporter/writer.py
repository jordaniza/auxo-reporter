import json
import functools
from tinydb import Query, TinyDB
from reporter import utils
from reporter.conf_generator import load_conf
from reporter.types import AccountState, Config, Reward, BaseReward

Account = Query()


from pydantic import BaseModel

EthereumAddress = str


class ClaimsRecipient(BaseModel):
    windowIndex: int
    accountIndex: int
    rewards: list[BaseReward]


class ClaimsWindow(BaseModel):
    windowIndex: int
    chainId: int
    aggregateRewards: list[Reward]
    recipients: dict[EthereumAddress, ClaimsRecipient]


def report_governance(db: TinyDB, path: str):
    gov_stats = db.table("governance_stats").all()[0]

    # stakers_fields = gov_stats["stakers"][0].keys()
    utils.write_json(gov_stats["stakers"], f"{path}/json/stakers.json")
    # utils.write_csv(gov_stats["stakers"], f"{path}/csv/stakers.csv", stakers_fields)

    # votes_fields = gov_stats["votes"][0].keys()
    # utils.write_csv(gov_stats["votes"], f"{path}/csv/votes.csv", votes_fields)

    # proposals_fields = gov_stats["proposals"][0].keys()
    # utils.write_csv(
    #     gov_stats["proposals"], f"{path}/csv/proposals.csv", proposals_fields
    # )

    # utils.write_list_csv(gov_stats["voters"], f"{path}/csv/voters.csv", "address")
    # utils.write_list_csv(
    #     gov_stats["non_voters"], f"{path}/csv/non_voters.csv", "address"
    # )


def report_rewards(db: TinyDB, path: str):
    distribution = db.table("distribution").all()

    # distribution_fields = distribution[0].keys()
    utils.write_json(distribution, f"{path}/json/distribution.json")
    # utils.write_csv(distribution, f"{path}/csv/distribution.csv", distribution_fields)

    accounts = db.table("accounts").all()
    rewards = [{"address": a["address"], "rewards": a.get("rewards")} for a in accounts]

    # utils.write_csv(rewards, f"{path}/csv/rewards.csv", ["address", "amount"])
    utils.write_json(rewards, f"{path}/json/rewards.json")


def report_slashed(db: TinyDB, path: str):
    slashed_accounts = db.table("accounts").search(
        Account.state == AccountState.SLASHED.value
    )

    # utils.write_csv(
    # slashed_accounts, f"{path}/csv/slashed.csv", ["address", "slice_amount"]
    # )
    utils.write_json(slashed_accounts, f"{path}/json/slashed.json")


def build_claims(conf: Config, db: TinyDB, path: str):
    accounts = db.table("accounts").search(Account.state == AccountState.ACTIVE.value)

    recipients = {
        a["address"]: ClaimsRecipient(
            windowIndex=conf.distribution_window,
            accountIndex=idx,
            rewards=a.get("rewards"),
        ).dict()
        for idx, a in enumerate(accounts)
    }

    reward_window = ClaimsWindow(
        windowIndex=conf.distribution_window,
        chainId=1,
        aggregateRewards=conf.rewards,
        recipients=recipients,
    )

    utils.write_json(reward_window.dict(), f"{path}/claims.json")


def main(path: str):
    conf = load_conf(path)
    db = utils.get_db(path)

    build_claims(conf, db, path)
    # report_rewards(db, path)
    # report_governance(db, path)
    # report_slashed(db, path)
