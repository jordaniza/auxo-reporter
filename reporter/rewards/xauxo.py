from decimal import Decimal
from typing import Tuple
from copy import deepcopy
from reporter.models import (
    Account,
    AccountState,
    Config,
    ERC20Amount,
    NormalizedRedistributionWeight as NRW,
    RedistributionOption,
    RedistributionWeight,
    TokenSummaryStats,
    RedistributionContainer,
    XAuxoRewardSummary,
    RewardSummary,
    XAuxoTaxCalculator,
)

from reporter.queries import (
    get_prv_stakers,
    prv_stakers_to_accounts,
    get_prv_total_supply,
)
from reporter.rewards.common import compute_rewards


def prv_active_rewards(
    prv_stats: TokenSummaryStats,
    total_rewards: Decimal,
) -> tuple[Decimal, Decimal]:
    """
    Divide PRV rewards into 2 buckets
    - active rewards are based on number of staked xauxo
    - inactive are rewards that would have accrued to stakers if they were active

    Inactive rewards will get redistributed according to DAO policies
    """

    total_supply = Decimal(prv_stats.total)
    pro_rata = Decimal(0) if total_supply == 0 else total_rewards / total_supply
    inactive_rewards = Decimal(prv_stats.inactive) * pro_rata / total_supply
    active_rewards = Decimal(prv_stats.active) * pro_rata / total_supply

    return active_rewards, inactive_rewards


def compute_prv_token_stats(
    accounts: list[Account], total_supply: Decimal
) -> TokenSummaryStats:
    """
    Computes summary statistics for a token based on a list of accounts holding that token.

    Args:
        accounts: A list of Account objects representing the accounts holding the token.
        total_supply: The total supply of the token.

    Returns:
        A TokenSummaryStats object containing the total, active, and inactive amounts of the token.

    """
    active = sum(int(a.token.amount) for a in accounts)
    return TokenSummaryStats(
        total=str(total_supply),
        active=str(active),
        inactive=str(int(total_supply) - active),
    )


def transfer_redistribution(
    accounts: list[Account], r: RedistributionWeight, conf: Config
) -> None:
    """
    Redistributes rewards from a transfer to a specific account.
    Args:
        accounts: A list of Account objects representing the accounts that may receive the transfer.
        r: A RedistributionWeight object specifying the account address and transfer amount.
        conf: A Config object containing information on reward tokens.
    """
    # check to see if the account already is due to receive rewards
    found_account = False
    for account in accounts:
        # account found, add the additional transfer
        if account.address == r.address:
            found_account = True
            account.notes.append(f"Transfer of {r.rewards}")
            account.rewards.amount = str(int(account.rewards.amount) + int(r.rewards))

    # cant find the account in the list this is a new account (like a multisig)
    # set it as inactive and add the transfer
    if not found_account:
        accounts.append(
            Account(
                address=r.address,
                token=ERC20Amount.xAUXO(amount="0"),
                rewards=conf.reward_token(amount=str(r.rewards)),
                state=AccountState.INACTIVE,
                notes=[f"Transfer of {r.rewards}"],
            )
        )


def redistribute(
    _accounts: list[Account], container: RedistributionContainer, conf: Config
) -> list[Account]:
    """
    Redistributes rewards to accounts based on a list of redistribution weights.
    Args:
        accounts: A list of Account objects representing accounts to receive rewards.
        redistributions: A list of RedistributionWeight objects specifying the rewards to be distributed.
        conf: A Config object containing information on reward tokens.
    Returns:
        the updated accounts list
    """
    # copy so as not to modify the original
    accounts = deepcopy(_accounts)

    # go through the accounts and make any manual transfers
    for r in container.n_redistributions:
        if r.option == RedistributionOption.TRANSFER:
            transfer_redistribution(accounts, r, conf)
    return accounts


def create_prv_reward_summary(
    distribution_rewards: RewardSummary,
    container: RedistributionContainer,
) -> XAuxoRewardSummary:
    summary = XAuxoRewardSummary.from_existing(distribution_rewards)
    summary.add_redistribution_data(container.to_stakers, container.transferred)
    return summary


def calculate_xauxo_rewards(config: Config, veauxo_rewards_to_xauxo: str):

    # apply a tax to the total xauxo rewards
    xauxo_rewards_pre_tax = config.reward_token(
        veauxo_rewards_to_xauxo
    )  # veauxo_reward_summaries.to_xauxo
    xauxo_tax = XAuxoTaxCalculator(config.xauxo_tax_percentage, xauxo_rewards_pre_tax)

    # fetch the list of accounts and compute active vs. total
    xauxo_stakers = get_prv_stakers()
    xauxo_accounts_in = prv_stakers_to_accounts(xauxo_stakers, config)
    xauxo_stats = compute_prv_token_stats(xauxo_accounts_in, get_prv_total_supply())

    # determine the split of active vs. inactive rewards,
    # and redistribute inactive rewards according to the config parameters
    (active, inactive) = prv_active_rewards(xauxo_stats, xauxo_tax)
    (
        redistributions,
        stakers_rewards,
        redistributed_to_stakers,
    ) = normalize_redistributions(config.redistributions, active, inactive)
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
    summary = create_prv_reward_summary(
        distribution_rewards,
        xauxo_tax,
        Decimal(redistributed_to_stakers),
        redistributed_transfer,
    )

    return summary, xauxo_accounts_out, xauxo_stats
