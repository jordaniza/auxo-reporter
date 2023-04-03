from __future__ import annotations
from enum import Enum
from pydantic import BaseModel, validator
import eth_utils as eth

from reporter.models.types import EthereumAddress
from reporter.models.ERC20 import PRV, ARV, ERC20Amount


class AccountState(str, Enum):
    """
    :state ACTIVE: the account voted this month
    :state INACTIVE: the account failed to vote this month and rewards are zero
    """

    ACTIVE = "active"
    INACTIVE = "inactive"


class User(BaseModel):
    """Base class for a user with an eth address"""

    address: EthereumAddress

    @validator("address")
    @classmethod
    def checksum_address(cls, input: str):
        return eth.to_checksum_address(input)


class Staker(User):
    """Base class for a user with a token balance"""

    token: ERC20Amount


class ARVStaker(Staker):
    """
    ARVStaker is a user with a token balance
    """

    def __init__(self, arv_holding: str, **kwargs):
        super().__init__(token=ARV(amount=arv_holding), **kwargs)


class PRVStaker(Staker):
    """
    PRVStaker is a user with a token balance
    """

    def __init__(self, prv_holding: str, **kwargs):
        super().__init__(token=PRV(amount=prv_holding), **kwargs)


class Account(Staker):
    """
    Information about Staker's ethereum account as it relates to the reward distribution
    :param `rewards`: the rewards that the account will receive this month. Will be zero if slashed
    :param `state`: whether the account was active or inactive this month
    :param `notes`: added to indicate why rewards were added
    """

    rewards: ERC20Amount
    state: AccountState
    notes: list[str] = []

    @staticmethod
    def from_prv_staker(
        staker: PRVStaker, rewards: ERC20Amount, state: AccountState
    ) -> Account:
        return Account(**staker.dict(), rewards=rewards, state=state)

    @staticmethod
    def from_arv_staker(
        staker: ARVStaker, rewards: ERC20Amount, state: AccountState
    ) -> Account:
        return Account(**staker.dict(), rewards=rewards, state=state)
