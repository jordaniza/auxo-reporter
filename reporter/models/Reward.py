from __future__ import annotations
from pydantic import validator, BaseModel
from reporter.models.types import BigNumber
from reporter.models.ERC20 import ERC20Amount
from typing import Optional
from decimal import Decimal
from dataclasses import dataclass


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

    # active rewards
    # inactive rewards?

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


@dataclass
class XAuxoTaxCalculator:
    tax_percent: float
    before_tax: ERC20Amount

    @property
    def tax(self) -> str:
        return str(int(Decimal(self.tax_percent) * Decimal(self.before_tax.amount)))

    @property
    def after_tax(self) -> str:
        return str(int(Decimal(self.before_tax.amount) - Decimal(self.tax)))


class XAuxoRewardSummary(RewardSummary):
    redistributed_total: BigNumber = "0"
    redistributed_to_stakers: BigNumber = "0"
    redistributed_transferred: BigNumber = "0"

    total_tax: BigNumber = "0"

    @staticmethod
    def from_existing(summary: RewardSummary) -> XAuxoRewardSummary:
        return XAuxoRewardSummary(**summary.dict())

    def add_tax_data(self, calculator: XAuxoTaxCalculator):
        self.total_tax = calculator.tax
        self.amount = calculator.after_tax

    def add_redistribution_data(self, to_stakers: Decimal, to_transfer: Decimal):
        self.redistributed_to_stakers = str(int(to_stakers))
        self.redistributed_transferred = str(int(to_transfer))
        self.redistributed_total = str(int(to_stakers + to_transfer))
