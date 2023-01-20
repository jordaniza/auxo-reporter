from typing import Optional, cast
from enum import Enum
from pydantic import validator, root_validator, BaseModel
from decimal import Decimal

from reporter.models.types import EthereumAddress, BigNumber
from reporter.errors import BadConfigException


class ERROR_MESSAGES:
    DUPLICATE_TRANSFER = "Passed Duplicate Transfer Addresses"
    DUPLICATE_XAUXO = "Passed multiple x auxo redistributions"
    VEAUXO_NOT_IMPLEMENTED = "veAUXO Redistribution is not supported yet"


class RedistributionOption(str, Enum):
    # add specific address to the merkle tree
    TRANSFER = "transfer"

    # redistribute rewards evenly amongst active xauxo stakers
    REDISTRIBUTE_XAUXO = "redistribute_xauxo"

    # redistribute rewards evently amongst active veauxo stakers
    REDISTRIBUTE_VEAUXO = "redistribute_veauxo"


# params
class RedistributionWeight(BaseModel):
    # weights will be normalized
    weight: float

    # if specifying a target address, put it here
    address: Optional[EthereumAddress]

    # choose whether to redistribute to an address
    # or return to stakers
    option: RedistributionOption

    distributed: bool = False
    rewards: BigNumber = "0"

    @validator("option")
    @classmethod
    def ensure_address_if_transfer(
        cls, option: RedistributionOption, values
    ) -> RedistributionOption:
        if option == RedistributionOption.TRANSFER and not values["address"]:
            raise BadConfigException(
                "Must provide a transfer address if not redistributing to stakers"
            )
        elif option != RedistributionOption.TRANSFER and values["address"]:
            raise BadConfigException(
                f"Cannot pass an address if redistributing, passed {values['address']}",
            )
        return option


class NormalizedRedistributionWeight(RedistributionWeight):
    total_weights: float
    normalized_weight: Optional[float]

    @root_validator
    @classmethod
    def normalize_weight(cls, values: dict):
        """
        We use a root validator to set the value of normalized weight directly
        """
        values["normalized_weight"] = values["weight"] / values["total_weights"]
        return values

    def distribute_inactive(self, total_inactive_rewards: BigNumber) -> None:
        weighted_rewards = Decimal(total_inactive_rewards) * Decimal(
            cast(float, self.normalized_weight)
        )
        self.rewards = str(weighted_rewards)
        self.distributed = True
