from __future__ import annotations
from pydantic import validator
from reporter.models.types import BigNumber
from reporter.models.ERC20 import ERC20Amount
from typing import Optional


class RewardSummary(ERC20Amount):
    """
    Extends the Reward object by giving the `pro_rata` reward per veToken
    Example: 1000 Wei per veToken

    Note: because tokens may have different decimal values, it can be tricky to display.
    For fractional reward tokens, we preserve the fraction up to 18 decimal points.
    """

    pro_rata: BigNumber
    # we need to confirm:
    # we need to have a view of rewards paid per active token
    # and rewards paid per total tokens
    # they are different and both need to be logged
    non_active_pro_rata: Optional[BigNumber] = None

    @validator("pro_rata")
    @classmethod
    def transform_pro_rata(cls, p: str):
        if float(p) >= 1:
            return str(int(float(p)))
        else:
            return f"{float(p):.18f}"


class VeAuxoRewardSummary(RewardSummary):
    to_xauxo: BigNumber = "0"

    @staticmethod
    def from_existing(summary: RewardSummary) -> VeAuxoRewardSummary:
        return VeAuxoRewardSummary(**summary.dict())


class XAuxoRewardSummary(RewardSummary):
    redistributed_total: BigNumber = "0"
    redistributed_to_stakers: BigNumber = "0"
    redistributed_transferred: BigNumber = "0"

    total_haircut: BigNumber = "0"

    @staticmethod
    def from_existing(summary: RewardSummary) -> XAuxoRewardSummary:
        return XAuxoRewardSummary(**summary.dict())
