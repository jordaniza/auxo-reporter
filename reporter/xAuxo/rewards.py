# **Option 1: Calculate from veAUXO**

# 1. Take the total veAUXO held by the Staking Manager (representing all xAUXO deposits)
# 2. Set total rewards *initially* allocated to xAUXO as `rewardPerActiveVeToken` * `StakingManagerVeTokenBalance`
# 3. Remove x% of rewards as `xAUXOPremium` and save
# 4. Calculate the quantity of inactive xAUXO tokens
# 5. Remove these rewards from circulation (or redistribute) and save
#     1. If redistributing:
#         1. Get total active tokens
#         2. Compute the xAUXOPerActiveToken
#     2. If not
#         1. Get rewards per token as veAUXO held by staking manager / xAUXO reward total


# edge cases: multiple of same address, multiple types aside from transfer, transfer to existing rewards address (combine)
from reporter.types import (
    EthereumAddress,
    Account,
    AccountState,
    ERC20Metadata,
    TokenSummaryStats,
    BaseERC20Holding,
    Config,
)
from tinydb import TinyDB
from reporter.rewards import compute_rewards, compute_token_stats
from pydantic import (
    BaseModel,
    Field,
    validator,
    ValidationError,
    parse_file_as,
    root_validator,
)
from typing import Optional, Tuple, cast
from enum import Enum
from decimal import Decimal
import functools
from reporter.errors import InvalidXAUXOHaircutPercentageException, BadConfigException
from reporter.conf_generator import XAUXO_ADDRESS, X_AUXO_HAIRCUT_PERCENT


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
    rewards: str = "0"

    @validator("option")
    @classmethod
    def ensure_address_if_transfer(
        cls, option: RedistributionOption, values
    ) -> RedistributionOption:
        if option == RedistributionOption.TRANSFER and not values["address"]:
            raise ValidationError(
                "Must provide a transfer address if not redistributing to stakers", cls
            )
        elif option != RedistributionOption.TRANSFER and values["address"]:
            raise ValidationError(
                f"Cannot pass an address if redistributing, passed {values['address']}",
                cls,
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


def compute_x_auxo_reward_total(
    total_xauxo_tokens: Decimal,
) -> Tuple[ERC20Metadata, int]:
    # TODO move to env file
    if X_AUXO_HAIRCUT_PERCENT > 1 or X_AUXO_HAIRCUT_PERCENT < 0:
        raise InvalidXAUXOHaircutPercentageException(
            f"xAUXO Haircut must be between 0 and 1 inclusive, received {X_AUXO_HAIRCUT_PERCENT}"
        )

    haircut_total = total_xauxo_tokens * Decimal(X_AUXO_HAIRCUT_PERCENT)
    xauxo_total = total_xauxo_tokens - haircut_total

    return (
        ERC20Metadata(
            decimals=18,
            symbol="xAUXO",
            amount=str(xauxo_total),
            address=XAUXO_ADDRESS,
        ),
        int(float(haircut_total)),
    )


def compute_xauxo_rewards(
    xauxo_stats: TokenSummaryStats,
    redistributions: list[RedistributionWeight],
    total_rewards_for_xauxo: ERC20Metadata,  # we need to haircut this
):

    pro_rata_rewards_per_token = (
        Decimal(total_rewards_for_xauxo.amount) / Decimal(xauxo_stats.total)
    ) * Decimal(10**total_rewards_for_xauxo.decimals)

    # reallocate based on weights
    inactive_tokens = Decimal(xauxo_stats.inactive)
    active_tokens = Decimal(xauxo_stats.active)

    inactive_rewards = (
        inactive_tokens
        * pro_rata_rewards_per_token
        / Decimal(10**total_rewards_for_xauxo.decimals)
    )

    active_rewards = (
        active_tokens
        * pro_rata_rewards_per_token
        / Decimal(10**total_rewards_for_xauxo.decimals)
    )

    print(f"Inactive xAUXO: {int(inactive_tokens)/10**18}")
    print(f"Active xAUXO: {int(xauxo_stats.active)/10**18}")
    print(f"Total xAUXO: {int(xauxo_stats.total)/10**18}")
    print(
        f"Inactive xAUXO %: {int(xauxo_stats.inactive)*100/int(xauxo_stats.total):.2f}"
    )
    print(f"Inactive Eth Value: {int(inactive_rewards)/10**18}")
    print(
        f"Inactive Eth %: {float(inactive_rewards)*100/float(total_rewards_for_xauxo.amount):.2f}"
    )
    print(f"Pro Rata: {int(pro_rata_rewards_per_token)/10**18}")
    print(f"total_rewards: {float(total_rewards_for_xauxo.amount)/10**18}")

    # redistributions
    total_weights = functools.reduce(
        lambda prev, curr: curr.weight + prev, redistributions, float(0)
    )
    normalized_redistributions: list[NormalizedRedistributionWeight] = [
        NormalizedRedistributionWeight(total_weights=total_weights, **r.dict())
        for r in redistributions
    ]

    for n in normalized_redistributions:
        n.rewards = str(
            int(inactive_rewards * Decimal(cast(float, n.normalized_weight)))
        )  # normalized is computed so is 'optional' according to pydantic, cast it to definite here
        n.distributed = True

    # add to the existing stakers rewards
    redistributed_to_stakers = "0"
    for n in normalized_redistributions:
        if n.option == RedistributionOption.REDISTRIBUTE_XAUXO:
            active_rewards += Decimal(n.rewards)
            redistributed_to_stakers = n.rewards

    # add accounts later

    return normalized_redistributions, active_rewards, redistributed_to_stakers


class ERROR_MESSAGES:
    DUPLICATE_TRANSFER = "Passed Duplicate Transfer Addresses"
    DUPLICATE_XAUXO = "Passed multiple x auxo redistributions"
    VEAUXO_NOT_IMPLEMENTED = "veAUXO Redistribution is not supported yet"


def load_redistributions(path: str) -> list[RedistributionWeight]:
    """
    Load and validate the redistributions array located at `path`
    """
    loaded = parse_file_as(list[RedistributionWeight], path)

    addresses = [l.address for l in loaded if l.address is not None]
    if len(set(addresses)) != len(addresses):
        raise BadConfigException(ERROR_MESSAGES.DUPLICATE_TRANSFER)

    redistribute_option_x_auxo = [
        l.option for l in loaded if l.option == RedistributionOption.REDISTRIBUTE_XAUXO
    ]
    if len(redistribute_option_x_auxo) > 1:
        raise BadConfigException(ERROR_MESSAGES.DUPLICATE_XAUXO)

    redistribute_option_ve_auxo = [
        l.option for l in loaded if l.option == RedistributionOption.REDISTRIBUTE_VEAUXO
    ]
    if len(redistribute_option_ve_auxo) > 0:
        raise BadConfigException(ERROR_MESSAGES.VEAUXO_NOT_IMPLEMENTED)

    return loaded


def compute_allocations(
    accounts: list[Account],
    xauxo_rewards: ERC20Metadata,  # or haircut here
    dist: list[RedistributionWeight],
):
    xauxo_stats = compute_token_stats(accounts)

    # we need to work out what are the xAUXO redistributions
    # we can work out xauxo rewards here
    (
        redistributions,
        stakers_rewards,
        redistributed_to_stakers,
    ) = compute_xauxo_rewards(xauxo_stats, dist, xauxo_rewards)

    redistributed_transfer = Decimal(0)
    # add any transfer addresses to rewards
    for r in redistributions:
        # Add any transfers to the stakers rewards list
        if r.option == RedistributionOption.TRANSFER:
            redistributed_transfer = redistributed_transfer + Decimal(r.rewards)

            # check to see if the account already is due to receive rewards
            found_account = False
            for account in accounts:
                if account.address == r.address:
                    found_account = True
                    account.notes.append(f"Redistributed transfer of {r.rewards}")
                    account.rewards = str(int(account.rewards) + int(r.rewards))

            if not found_account:
                accounts.append(
                    Account(
                        address=r.address,
                        token=BaseERC20Holding(amount=0, address=XAUXO_ADDRESS),
                        rewards=str(r.rewards),
                        state=AccountState.INACTIVE,
                        notes=[f"Redistributed transfer of {r.rewards}"],
                    )
                )

    return (
        xauxo_stats,
        accounts,
        redistributions,
        stakers_rewards,
        redistributed_to_stakers,
        redistributed_transfer,
    )
