from __future__ import annotations
from typing import Union, Literal
import eth_utils as eth
from pydantic import BaseModel, validator

from reporter.models.types import EthereumAddress, BigNumber

# from reporter.models.Config import Config
from reporter.env import ADDRESSES

AUXO_TOKEN_NAMES = Union[Literal["veAUXO"], Literal["xAUXO"]]


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


class ERC20Amount(ERC20Metadata):
    """
    Hold ERC20 data with an amount
    The significance of the amount will depend on context
    i.e. "user's balance" vs "rewards assigned"
    """

    amount: BigNumber

    @staticmethod
    def xAUXO(amount: str) -> ERC20Amount:
        return ERC20Amount(**xAUXO.dict(), amount=amount)

    @staticmethod
    def veAUXO(amount: str) -> ERC20Amount:
        return ERC20Amount(**veAUXO.dict(), amount=amount)
