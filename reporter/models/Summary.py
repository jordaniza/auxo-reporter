from pydantic import BaseModel
from reporter.models.types import BigNumber


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
