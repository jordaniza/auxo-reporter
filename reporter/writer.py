from tinydb import TinyDB

from reporter import utils
from reporter.conf_generator import load_conf
from reporter.models import AUXO_TOKEN_NAMES, ClaimsRecipient, Config


def report_governance(db: TinyDB, path: str):
    gov_stats = db.table("governance_stats").all()[0]

    stakers_fields = gov_stats["stakers"][0].keys()
    utils.write_json(gov_stats["stakers"], f"{path}/json/stakers.json")
    utils.write_csv(gov_stats["stakers"], f"{path}/csv/stakers.csv", stakers_fields)

    votes_fields = gov_stats["votes"][0].keys()
    utils.write_csv(gov_stats["votes"], f"{path}/csv/votes.csv", votes_fields)

    proposals_fields = gov_stats["proposals"][0].keys()
    utils.write_csv(
        gov_stats["proposals"], f"{path}/csv/proposals.csv", proposals_fields
    )

    utils.write_list_csv(gov_stats["voters"], f"{path}/csv/voters.csv", "address")
    utils.write_list_csv(
        gov_stats["non_voters"], f"{path}/csv/non_voters.csv", "address"
    )


def report_rewards(db: TinyDB, path: str, token_name: AUXO_TOKEN_NAMES = "veAUXO"):
    accounts = db.table(f"{token_name}_holders").all()

    rewards = [{"address": a["address"], "rewards": a["rewards"]} for a in accounts]

    utils.write_csv(rewards, f"{path}/csv/rewards.csv", ["address", "rewards"])
    utils.write_json(rewards, f"{path}/json/rewards.json")


from tinydb import where


def build_claims(
    conf: Config, db: TinyDB, path: str, token_name: AUXO_TOKEN_NAMES = "veAUXO"
):
    accounts = db.table(f"{token_name}_holders").search(
        where("rewards")["amount"].map(int) > 0
    )

    rewards = db.table(f"{token_name}_stats").all()[0]["rewards"]

    recipients = {
        a["address"]: ClaimsRecipient(
            windowIndex=conf.distribution_window,
            accountIndex=idx,
            rewards=a["rewards"]["amount"],
        ).dict()
        for idx, a in enumerate(accounts)
    }

    reward_window = {
        "windowIndex": conf.distribution_window,
        "chainId": 1,
        "aggregateRewards": rewards,
        "recipients": recipients,
    }

    utils.write_json(reward_window, f"{path}/claims-{token_name}.json")
    print(
        f"🚀🚀🚀 Successfully created the {token_name} claims database, check it and generate the merkle tree"
    )


def main(path: str):
    if not path:
        path = input(" Path to the config file ")
    conf = load_conf(path)
    db = utils.get_db(path)  # loads the reporter-db.json

    build_claims(conf, db, path)
    report_rewards(db, path)
    report_governance(db, path)
