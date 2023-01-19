from __future__ import annotations
from enum import Enum
from pydantic import BaseModel, validator
import eth_utils as eth

from reporter.models.types import EthereumAddress
from reporter.models.ERC20 import ERC20Amount, veAUXO, xAUXO


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
    """
    Staker is a user with a token balance
    """

    holding: ERC20Amount

    @staticmethod
    def veAuxo(user: EthereumAddress, veAuxoHolding: str) -> Staker:
        """Instatiate a staker with veAUXO"""
        holding = ERC20Amount.veAUXO(veAuxoHolding)
        return Staker(address=user, holding=holding)

    @staticmethod
    def xAuxo(user: EthereumAddress, xAuxoHolding: str) -> Staker:
        """Instatiate a staker with xAUXO"""
        holding = ERC20Amount.xAUXO(xAuxoHolding)
        return Staker(address=user, holding=holding)


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
    def from_staker(
        staker: Staker, rewards: ERC20Amount, state: AccountState
    ) -> Account:
        return Account(**staker.dict(), rewards=rewards, state=state)
