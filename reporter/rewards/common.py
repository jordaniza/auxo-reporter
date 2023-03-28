import itertools
from decimal import Decimal

from reporter.models import (
    Account,
    AccountState,
    ERC20Amount,
    RewardSummary,
)


def distribute_rewards(account: Account, pro_rata: Decimal) -> Account:
    """
    Add the rewards for he account, for a particular token.
    :param `account`: the account to add rewards to
    :param `pro_rata`: quantity of reward token to be add per token units held by account

    Slashed accounts will be appended a reward entry with an amount equal to zero
    """

    if account.state == AccountState.ACTIVE:
        account_reward = int(pro_rata * Decimal(account.token.amount))
        account.rewards.amount = str(Decimal(account.rewards.amount) + account_reward)
        account.notes.append(f"active reward of {account_reward}")

    return account


def compute_rewards(
    total_rewards: ERC20Amount, total_active_tokens: Decimal, accounts: list[Account]
) -> tuple[list[Account], RewardSummary]:
    """

    Add the rewards that will be distributed across all users, including the pro-rata reward rate for each token
    Modifies the accounts object to add rewards

    :param `total_rewards`: rewards token with total quantities to distribute amongst stakers
    :param `total_active_tokens`: tokens belonging to active stakers (total - inactive)
    :param `accounts`: base array of Account objects that have yet to have rewards added
    """

    # compute rewards per veToken held, for the given reward token

    pro_rata = (
        0
        if total_active_tokens == 0
        else Decimal(total_rewards.amount) / total_active_tokens
    )

    rewarded_accounts = list(
        map(
            distribute_rewards,  # type: ignore
            accounts,
            itertools.repeat(pro_rata),
        )
    )

    # add to summary
    distribution_rewards = RewardSummary(
        **total_rewards.dict(),
        pro_rata=str(pro_rata),
    )

    # TODO remainder?
    return rewarded_accounts, distribution_rewards
