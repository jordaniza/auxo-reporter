from __future__ import annotations

from typing import Literal, Optional, Union

import eth_utils as eth
from pydantic import BaseModel, validator

from reporter.env import ADDRESSES
from reporter.models.types import BigNumber, EthereumAddress

from datetime import datetime

AUXO_TOKEN_NAMES = Union[
    Literal["veAUXO"], Literal["xAUXO"], Literal["ARV"], Literal["PRV"]
]


class BaseERC20(BaseModel):
    """Simply holds the token address alongside an identifier"""

    address: EthereumAddress
    symbol: str

    @validator("address")
    @classmethod
    def checksum_token(cls, addr: EthereumAddress):
        return eth.to_checksum_address(addr)


class ERC20Metadata(BaseERC20):
    """Adds additional metadata about the token"""

    decimals: int


veAUXO = ERC20Metadata(address=ADDRESSES.VEAUXO, symbol="veAUXO", decimals=18)
xAUXO = ERC20Metadata(address=ADDRESSES.XAUXO, symbol="xAUXO", decimals=18)


class Lock(BaseModel):
    amount: BigNumber
    lockDuration: float
    lockedAt: float


class ARV(ERC20Metadata):
    """ARV token"""

    # holding of ARV
    amount: BigNumber

    # decayed holding of ARV factoring in the user's lock time
    decayed_amount: Optional[BigNumber]

    # details of the Auxo Lock
    lock: Optional[Lock]

    def __init__(self, **kwargs):
        super().__init__(decimals=18, address=ADDRESSES.VEAUXO, symbol="ARV", **kwargs)


class PRV(ERC20Metadata):
    """PRV token"""

    # holding of PRV in wallet
    amount: BigNumber

    # locked in RollStaker
    staked_amount: Optional[BigNumber]

    def __init__(self, **kwargs):
        super().__init__(decimals=18, address=ADDRESSES.PRV, symbol="PRV", **kwargs)


class ERC20Amount(ERC20Metadata):
    """
    Hold ERC20 data with an amount
    The significance of the amount will depend on context
    i.e. "user's balance" vs "rewards assigned"

    :param original_amount: before applying decay
    """

    amount: BigNumber

    @staticmethod
    def xAUXO(amount: str) -> ERC20Amount:
        return ERC20Amount(**xAUXO.dict(), amount=amount)

    @staticmethod
    def veAUXO(amount: str) -> ERC20Amount:
        return ERC20Amount(**veAUXO.dict(), amount=amount)
