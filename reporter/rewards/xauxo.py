from decimal import Decimal
from typing import Tuple

from reporter.models import (
    Account,
    AccountState,
    Config,
    ERC20Amount,
    NormalizedRedistributionWeight,
    RedistributionOption,
    RedistributionWeight,
    TokenSummaryStats,
)


def compute_x_auxo_reward_total(
    conf: Config,
    total_xauxo_rewards: Decimal,
) -> Tuple[ERC20Amount, int]:

    haircut_total = total_xauxo_rewards * Decimal(conf.xauxo_haircut)
    xauxo_total = total_xauxo_rewards - haircut_total

    return (
        ERC20Amount.xAUXO(str(xauxo_total)),
        int(float(haircut_total)),
    )


def compute_xauxo_rewards(
    xauxo_stats: TokenSummaryStats,
    redistributions: list[RedistributionWeight],
    total_rewards_for_xauxo: ERC20Amount,  # we need to haircut this
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

    # redistributions
    total_weights = sum(r.weight for r in redistributions)
    normalized_redistributions: list[NormalizedRedistributionWeight] = [
        NormalizedRedistributionWeight(total_weights=total_weights, **r.dict())
        for r in redistributions
    ]

    for n in normalized_redistributions:
        n.distribute_inactive(str(inactive_rewards))

    # add to the existing stakers rewards
    redistributed_to_stakers = "0"
    for n in normalized_redistributions:
        if n.option == RedistributionOption.REDISTRIBUTE_XAUXO:
            active_rewards += Decimal(n.rewards)
            redistributed_to_stakers = n.rewards

    # add accounts later
    return normalized_redistributions, active_rewards, redistributed_to_stakers


def compute_xauxo_token_stats(
    accounts: list[Account], total_supply: str
) -> TokenSummaryStats:
    active = sum(int(a.holding.amount) for a in accounts)
    return TokenSummaryStats(
        total=str(total_supply),
        active=str(active),
        inactive=str(int(total_supply) - active),
    )


def redistribute(
    accounts: list[Account], redistributions: list[RedistributionWeight], conf: Config
) -> Tuple[list[Account], Decimal]:
    redistributed_transfer = Decimal(0)
    # add any transfer addresses to rewards
    for r in redistributions:
        # Add any transfers to the stakers rewards list
        if r.option == RedistributionOption.TRANSFER:
            redistributed_transfer += Decimal(r.rewards)

            # check to see if the account already is due to receive rewards
            found_account = False
            for account in accounts:
                if account.address == r.address:
                    found_account = True
                    account.notes.append(f"Transfer of {r.rewards}")
                    account.rewards.amount = str(
                        int(account.rewards.amount) + int(r.rewards)
                    )

            if not found_account:
                accounts.append(
                    Account(
                        address=r.address,
                        holding=ERC20Amount.xAUXO(amount="0"),
                        rewards=conf.reward_token(amount=str(r.rewards)),
                        state=AccountState.INACTIVE,
                        notes=[f"Transfer of {r.rewards}"],
                    )
                )
    return accounts, redistributed_transfer
