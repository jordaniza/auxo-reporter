from __future__ import annotations
from typing import Optional
from decimal import Decimal
from pydantic import validator, BaseModel

from reporter.models.types import BigNumber
from reporter.models.ERC20 import ERC20Amount


class TokenSummaryStats(BaseModel):
    """
    Summarizes Token positions for active and inactive statuses
    :param `total`: total Tokens in circulation at block number
    :param `active`: total Tokens belonging to users that voted/eligible for rewards
    :param `inactive`: total Tokens belonging to user that did not vote. Their rewards will be redistributed.
    """

    total: BigNumber
    active: BigNumber
    inactive: BigNumber


class RewardSummary(ERC20Amount):
    """
    Extends the Reward object by giving the `pro_rata` reward per token
    Example: 1000 Wei per ARV token

    Note: because tokens may have different decimal values, it can be tricky to display.
    For fractional reward tokens, we preserve the fraction up to 18 decimal points.
    """

    pro_rata: BigNumber

    @validator("pro_rata")
    @classmethod
    def transform_pro_rata(cls, p: str):
        if float(p) >= 1:
            return str(int(float(p)))
        else:
            return f"{float(p):.18f}"


class ARVRewardSummary(RewardSummary):
    @staticmethod
    def from_existing(summary: RewardSummary) -> ARVRewardSummary:
        return ARVRewardSummary(**summary.dict())


class PRVRewardSummary(RewardSummary):
    redistributed_total: BigNumber = "0"
    redistributed_to_stakers: BigNumber = "0"
    redistributed_transferred: BigNumber = "0"

    @staticmethod
    def from_existing(summary: RewardSummary) -> PRVRewardSummary:
        return PRVRewardSummary(**summary.dict())

    def add_redistribution_data(self, to_stakers: Decimal, to_transfer: Decimal):
        self.redistributed_to_stakers = str(int(to_stakers))
        self.redistributed_transferred = str(int(to_transfer))
        self.redistributed_total = str(int(to_stakers + to_transfer))
        # redistributions to stakers already included as part of the distribution rewards
        # so we don't want to double count them here.
        self.amount = str(int(Decimal(self.amount)) + to_transfer)
