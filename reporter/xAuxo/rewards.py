import functools
from decimal import Decimal
from typing import Tuple, cast

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
from reporter.rewards import compute_token_stats


def compute_x_auxo_reward_total(
    conf: Config,
    total_xauxo_tokens: Decimal,
) -> Tuple[ERC20Amount, int]:

    haircut_total = total_xauxo_tokens * Decimal(conf.xauxo_haircut)
    xauxo_total = total_xauxo_tokens - haircut_total

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


def compute_allocations(
    accounts: list[Account],
    xauxo_rewards: ERC20Amount,  # or haircut here
    dist: list[RedistributionWeight],
    conf: Config,
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

    return (
        xauxo_stats,
        accounts,
        redistributions,
        stakers_rewards,
        redistributed_to_stakers,
        redistributed_transfer,
    )
