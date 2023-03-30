from typing import Optional, cast
from enum import Enum
from pydantic import validator, root_validator, BaseModel
from decimal import Decimal

from reporter.models.types import EthereumAddress, BigNumber
from reporter.errors import BadConfigException


class ERROR_MESSAGES:
    DUPLICATE_TRANSFER = "Passed Duplicate Transfer Addresses"
    DUPLICATE_XAUXO = "Passed multiple PRV redistributions"
    ARV_NOT_IMPLEMENTED = "ARV Redistribution is not supported yet"


class RedistributionOption(str, Enum):
    # add specific address to the merkle tree
    TRANSFER = "transfer"

    # redistribute rewards evenly amongst active xauxo stakers
    REDISTRIBUTE_PRV = "redistribute_prv"

    # redistribute rewards evently amongst active arv stakers
    REDISTRIBUTE_ARV = "redistribute_arv"


# params
class RedistributionWeight(BaseModel):
    """
    PRV gets a fixed allocation but some stakers will be inactive,
    this class determines how to redistribute rewards accrued by inactive stakers.
    each RedistributionWeight has a weight, which will be normalized to a percentage of the total rewards
    and an option, which determines how to redistribute the rewards.

    The total rewards attached to the redistribution weight will be distributed according to the option
    """

    # weights will be normalized
    weight: float

    # if specifying a target address, put it here
    address: Optional[EthereumAddress]

    # choose whether to redistribute to a specific address or return to stakers
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

    def set_reward(self, reward: Decimal, total_weights: float) -> None:
        """
        Takes rewards and multiplies by the normalized weight
        Records distributed as true and sets rewards to the computed value
        """
        normalized_weight = self.weight / total_weights
        decimal_reward = reward * Decimal(normalized_weight)
        self.rewards = str(int(decimal_reward))
        self.distributed = True


class RedistributionContainer(BaseModel):
    """
    A container for redistribution weights
    """

    redistributions: list[RedistributionWeight]
    total_redistributed: Decimal = Decimal(0)
    distributed: bool = False

    @property
    def total_weights(self) -> float:
        return sum(r.weight for r in self.redistributions)

    def redistribute(self, rewards: Decimal) -> None:
        """
        Takes inactive rewards and distributes them according to redistribution weights
        weights will be normalized and rewards will be distributed according to the option
        """
        for r in self.redistributions:
            r.set_reward(rewards, self.total_weights)
        self.total_redistributed = Decimal(rewards)
        self.distributed = True

    @property
    def transferred(self) -> Decimal:
        """
        Fetches quantity of rewards transferred to a specific addresses
        """
        if not self.distributed:
            return Decimal(0)

        transferred = Decimal(0)
        for r in self.redistributions:
            if r.option == RedistributionOption.TRANSFER:
                transferred += Decimal(r.rewards)
        return transferred

    @property
    def to_stakers(self) -> Decimal:
        """
        Fetches quantity of rewards transferred evenly amongst active stakers
        """
        if not self.distributed:
            return Decimal(0)

        to_stakers = Decimal(0)
        for r in self.redistributions:
            if r.option == RedistributionOption.REDISTRIBUTE_PRV:
                to_stakers += Decimal(r.rewards)
        return to_stakers
