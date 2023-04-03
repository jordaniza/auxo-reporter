import os
from typing import Optional
from decimal import Decimal
from tinydb import TinyDB, where
from utils import write_json
from reporter.models import (
    Account,
    AUXO_TOKEN_NAMES,
    ARVStaker,
    ARVRewardSummary,
    TokenSummaryStats,
    ClaimsRecipient,
    Vote,
    PRVRewardSummary,
    RewardSummary,
    Proposal,
    Config,
)
from reporter.errors import MissingSummaryError


class DB(TinyDB):
    config: Config
    arv_summary: Optional[ARVRewardSummary]
    prv_summary: Optional[PRVRewardSummary]

    def __init__(self, conf: Config, drop=False, **kwargs):
        self.config = conf
        self.arv_summary = None
        self.prv_summary = None
        path = f"reports/{conf.date}/reporter-db.json"

        # check if the directory exists
        create_dirs = self.exists(path) == False
        super().__init__(
            path,
            indent=4,
            create_dirs=create_dirs,
            **kwargs,
        )

        if drop:
            self.drop_tables()

    @staticmethod
    def exists(path: str):
        return os.path.exists(path)

    def write_distribution(
        self,
        distribution: list[Account],
        token_name: AUXO_TOKEN_NAMES,
    ):
        self.table(f"{token_name}_distribution").insert_multiple(
            [d.dict() for d in distribution]
        )

    def write_arv_stats(
        self,
        stakers: list[ARVStaker],
        votes: list[Vote],
        proposals: list[Proposal],
        voters: list[str],
        non_voters: list[str],
        rewards: ARVRewardSummary,
        tokenStats: TokenSummaryStats,
    ):
        self.table("ARV_stats").insert(
            {
                "stakers": len([s.dict() for s in stakers]),
                "votes": len([v.dict() for v in votes]),
                "proposals": len([p.dict() for p in proposals]),
                "voters": len(voters),
                "non_voters": len(non_voters),
                "rewards": rewards.dict(),
                "token_stats": tokenStats.dict(),
            },
        )
        self.arv_summary = rewards

    def write_prv_stats(
        self,
        accounts: list[Account],
        rewards: RewardSummary,
        tokenStats: TokenSummaryStats,
    ):
        prv_summary = PRVRewardSummary.from_existing(rewards)
        self.table("PRV_stats").insert(
            {
                "stakers": len(accounts),
                "rewards": prv_summary.dict(),
                "token_stats": tokenStats.dict(),
            }
        )
        self.prv_summary = prv_summary

    def get_aggregate_rewards(self, token_name: AUXO_TOKEN_NAMES):
        if token_name == "ARV":
            if not self.arv_summary:
                raise MissingSummaryError("ARV Summary not found")
            return self.arv_summary
        elif token_name == "PRV":
            if not self.prv_summary:
                raise MissingSummaryError("PRV Summary not found")
            return self.prv_summary

    def build_claims(self, token_name: AUXO_TOKEN_NAMES):
        distribution = self.table(f"{token_name}_distribution")

        rewards_accounts = distribution.search(
            where("rewards")["amount"].map(Decimal) > Decimal(0)
        )

        recipients = {
            ra["address"]: ClaimsRecipient(
                windowIndex=self.config.distribution_window,
                accountIndex=idx,
                rewards=ra["rewards"]["amount"],
                token=ra["rewards"]["address"],
            ).dict()
            for idx, ra in enumerate(rewards_accounts)
        }
        claims = {
            "windowIndex": self.config.distribution_window,
            "chainId": 1,
            "aggregateRewards": self.get_aggregate_rewards(token_name).dict(),
            "recipients": recipients,
        }
        write_json(claims, f"reports/{self.config.date}/claims-{token_name}.json")
        print(
            f"🚀🚀🚀 Successfully created the {token_name} claims database, check it and generate the merkle tree"
        )

    def write_claims_and_distribution(
        self, distribution: list[Account], token_name: AUXO_TOKEN_NAMES
    ):
        self.write_distribution(distribution, token_name)
        self.build_claims(token_name)
