import itertools
from decimal import Decimal
from copy import deepcopy

from reporter.models import (
    Account,
    AccountState,
    ERC20Amount,
    RewardSummary,
)


def distribute_rewards(account: Account, pro_rata: Decimal) -> Account:
    """
    Add the rewards for the account, for a particular token.
    :param `account`: the account to add rewards to
    :param `pro_rata`: quantity of reward token to be add per token units held by account
    """
    # pass by reference can cause errors, so we allocate a new item in memory
    new_account = deepcopy(account)
    if account.state == AccountState.ACTIVE:
        account_reward = int(pro_rata * Decimal(account.token.amount))
        new_account.rewards.amount = str(
            Decimal(account.rewards.amount) + account_reward
        )
        new_account.notes.append(f"active reward of {account_reward}")
    return new_account


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
    """ 
    the active rewards are correctly inserted as a string
    but the total is incorrect
    
    """

    # add to summary
    distribution_rewards = RewardSummary(
        **total_rewards.dict(),
        pro_rata=str(pro_rata),
    )

    return rewarded_accounts, distribution_rewards
