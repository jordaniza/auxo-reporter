from __future__ import annotations

from typing import Literal, Optional, Union

import eth_utils as eth
from pydantic import BaseModel, validator

from reporter.env import ADDRESSES
from reporter.models.types import BigNumber, EthereumAddress

AUXO_TOKEN_NAMES = Union[Literal["ARV"], Literal["PRV"]]


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


class ERC20Amount(ERC20Metadata):
    """Adds the amount of tokens held by the user"""

    amount: BigNumber


class Lock(BaseModel):
    amount: BigNumber
    lockDuration: int
    lockedAt: int


class ARV(ERC20Amount):
    """ARV token"""

    # original amount of tokens, excluding the boost/decay mechanic
    non_decayed_amount: Optional[BigNumber]

    # details of the Auxo Lock
    lock: Optional[Lock]

    def __init__(self, **kwargs):
        super().__init__(decimals=18, address=ADDRESSES.ARV, symbol="ARV", **kwargs)


class PRV(ERC20Amount):
    """PRV token"""

    def __init__(self, **kwargs):
        super().__init__(decimals=18, address=ADDRESSES.PRV, symbol="PRV", **kwargs)
