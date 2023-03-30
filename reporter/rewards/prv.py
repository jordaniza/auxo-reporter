from decimal import Decimal
from copy import deepcopy
from reporter.models import (
    Account,
    AccountState,
    Config,
    PRV,
    RedistributionOption,
    RedistributionWeight,
    TokenSummaryStats,
    RedistributionContainer,
    PRVRewardSummary,
    RewardSummary,
)


def prv_active_rewards(
    prv_stats: TokenSummaryStats,
    total_rewards: Decimal,
) -> tuple[Decimal, Decimal]:
    """
    Divide PRV rewards into 2 buckets
    - active rewards are based on number of staked PRV
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
                token=PRV(amount="0"),
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
) -> PRVRewardSummary:
    summary = PRVRewardSummary.from_existing(distribution_rewards)
    summary.add_redistribution_data(container.to_stakers, container.transferred)
    return summary
