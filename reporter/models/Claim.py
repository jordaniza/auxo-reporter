from typing import Union

from pydantic import BaseModel

from reporter.models.Reward import ARVRewardSummary, PRVRewardSummary
from reporter.models.types import BigNumber, EthereumAddress


class ClaimsRecipient(BaseModel):
    """
    Minimal claim data for each recipient that will be used to generate the merkle tree
    :param `windowIndex`: distribution index, should be unique
    :param `accountIndex`: autoincrementing but unique index of claim within a window.
    Used by the MerkleDistributor to efficiently index on-chain claiming.
    """

    windowIndex: int
    accountIndex: int
    rewards: BigNumber
    token: EthereumAddress


class ClaimsWindow(BaseModel):
    """
    The full claim data used to generate the tree. The tree doesn't use anything other than
    the recipients data, so the additional metadata in `aggregateRewards` is purely for readability.
    """

    windowIndex: int
    chainId: int
    aggregateRewards: Union[ARVRewardSummary, PRVRewardSummary]
    recipients: dict[EthereumAddress, ClaimsRecipient]
