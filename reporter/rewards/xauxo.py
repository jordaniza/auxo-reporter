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
    XAuxoRewardSummary,
    RewardSummary,
    XAuxoTaxCalculator,
)

from reporter.queries import get_xauxo_stakers, xauxo_accounts, get_xauxo_total_supply
from reporter.rewards.common import compute_rewards


def compute_active_rewards(
    xauxo_stats: TokenSummaryStats,
    tax_calulator: XAuxoTaxCalculator,
):
    """
    Divide xauxo rewards into 2 buckets
    - active rewards are based on number of staked xauxo
    - inactive are rewards that would have accrued to stakers if they were active

    Inactive rewards will get redistributed according to DAO policies
    """

    pro_rata_rewards_per_token = (
        Decimal(tax_calulator.before_tax.amount) / Decimal(xauxo_stats.total)
    ) * Decimal(10**tax_calulator.before_tax.decimals)

    # reallocate based on weights
    inactive_tokens = Decimal(xauxo_stats.inactive)
    active_tokens = Decimal(xauxo_stats.active)

    inactive_rewards = (
        inactive_tokens
        * pro_rata_rewards_per_token
        / Decimal(10**tax_calulator.before_tax.decimals)
    )

    active_rewards = (
        active_tokens
        * pro_rata_rewards_per_token
        / Decimal(10**tax_calulator.before_tax.decimals)
    )

    return active_rewards, inactive_rewards


def compute_xauxo_redistributions(
    redistributions: list[RedistributionWeight],
    active_rewards: Decimal,
    inactive_rewards: Decimal,
):
    """
    Redistribute inactive rewards according to config parameters
    Return the list of redistributions, along with the total rewards stakers will receive
    and log the amount redistributed to said stakers
    """

    stakers_total_rewards = active_rewards

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
            stakers_total_rewards += Decimal(n.rewards)
            redistributed_to_stakers = n.rewards

    # add accounts later
    return normalized_redistributions, stakers_total_rewards, redistributed_to_stakers


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


def compute_x_auxo_reward_total(
    conf: Config,
    total_xauxo_rewards: Decimal,
) -> Tuple[ERC20Amount, int]:

    haircut_total = total_xauxo_rewards * Decimal(conf.xauxo_tax_percentage)
    xauxo_total = total_xauxo_rewards - haircut_total

    return (
        ERC20Amount.xAUXO(str(xauxo_total)),
        int(float(haircut_total)),
    )


def create_xauxo_reward_summary(
    distribution_rewards: RewardSummary,
    tax_calculator: XAuxoTaxCalculator,
    redistributed_to_stakers: Decimal,
    redistributed_transfer: Decimal,
) -> XAuxoRewardSummary:
    summary = XAuxoRewardSummary.from_existing(distribution_rewards)
    summary.add_tax_data(tax_calculator)
    summary.add_redistribution_data(redistributed_to_stakers, redistributed_transfer)
    return summary


def calculate_xauxo_rewards(config: Config, veauxo_rewards_to_xauxo: str):

    # apply a tax to the total xauxo rewards
    xauxo_rewards_pre_tax = config.reward_token(
        veauxo_rewards_to_xauxo
    )  # veauxo_reward_summaries.to_xauxo
    xauxo_tax = XAuxoTaxCalculator(config.xauxo_tax_percentage, xauxo_rewards_pre_tax)

    # fetch the list of accounts and compute active vs. total
    xauxo_stakers = get_xauxo_stakers()
    xauxo_accounts_in = xauxo_accounts(xauxo_stakers, config)
    xauxo_stats = compute_xauxo_token_stats(xauxo_accounts_in, get_xauxo_total_supply())

    # determine the split of active vs. inactive rewards,
    # and redistribute inactive rewards according to the config parameters
    (active, inactive) = compute_active_rewards(xauxo_stats, xauxo_tax)
    (
        redistributions,
        stakers_rewards,
        redistributed_to_stakers,
    ) = compute_xauxo_redistributions(config.redistributions, active, inactive)
    xauxo_accounts_out, redistributed_transfer = redistribute(
        xauxo_accounts_in, redistributions, config
    )

    # action the rewards distribution across xauxo stakers
    xauxo_stakers_net_redistributed = config.reward_token(str(int(stakers_rewards)))
    xauxo_accounts_out, distribution_rewards = compute_rewards(
        xauxo_stakers_net_redistributed,
        Decimal(xauxo_stats.active),
        xauxo_accounts_out,
    )

    # yield the summary for reporting
    summary = create_xauxo_reward_summary(
        distribution_rewards,
        xauxo_tax,
        Decimal(redistributed_to_stakers),
        redistributed_transfer,
    )

    return summary, xauxo_accounts_out, xauxo_stats
