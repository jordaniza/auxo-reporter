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
    Proposal,
)
from decimal import Decimal


class DB(TinyDB):
    directory: str
    path: str

    def __init__(self, directory: str, drop=False, **kwargs):
        self.directory = directory
        self.path = f"{directory}/reporter-db.json"
        create_dirs = False
        try:
            super().__init__(
                self.path,
                indent=4,
                create_dirs=create_dirs,
                **kwargs,
            )
        except FileNotFoundError:
            create_dirs = True
            super().__init__(
                self.path,
                indent=4,
                create_dirs=create_dirs,
                **kwargs,
            )

        if drop:
            self.drop_tables()

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

    def build_claims(self, window_index: int, token_name: AUXO_TOKEN_NAMES):
        distribution = self.table(f"{token_name}_distribution")

        rewards_accounts = distribution.search(
            where("rewards")["amount"].map(Decimal) > Decimal(0)
        )

        recipients = {
            ra["address"]: ClaimsRecipient(
                windowIndex=window_index,
                accountIndex=idx,
                rewards=ra["rewards"]["amount"],
                token=ra["rewards"]["address"],
            ).dict()
            for idx, ra in enumerate(rewards_accounts)
        }
        claims = {
            "windowIndex": window_index,
            "chainId": 1,
            "aggregateRewards": distribution.all()[0]["rewards"],
            "recipients": recipients,
        }
        write_json(claims, f"{self.directory}/claims-{token_name}.json")
        print(
            f"🚀🚀🚀 Successfully created the {token_name} claims database, check it and generate the merkle tree"
        )
