from pydantic import validator
from reporter.models.types import BigNumber
from reporter.models.ERC20 import ERC20Amount


class RewardSummary(ERC20Amount):
    """
    Extends the Reward object by giving the `pro_rata` reward per veToken
    Example: 1000 Wei per veToken

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


class VeAuxoRewardSummary(RewardSummary):
    to_xauxo: BigNumber = "0"


class XAuxoRewardSummary(RewardSummary):
    redistributed_total: BigNumber = "0"
    redistributed_to_stakers: BigNumber = "0"
    redistributed_transferred: BigNumber = "0"

    total_haircut: BigNumber = "0"
