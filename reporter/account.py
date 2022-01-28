from enum import Enum
from tinydb import Query

Account = Query()


class AccountState(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SLASHED = "slashed"


def to_staker(staker):
    return {"address": staker[0], "balance": int(staker[1])}


def state(voted, inactive_windows):
    if voted:
        return AccountState.ACTIVE.value

    # check if inactive windows are consecutive

    end_slice = inactive_windows[-3:]

    slashed = len(end_slice) == 3 and sorted(end_slice) == list(
        range(min(end_slice), max(end_slice) + 1)
    )

    return AccountState.INACTIVE.value if not slashed else AccountState.SLASHED.value


def init_account(staker, db, window_index, participation, claim_map):
    account_prev = db.table("accounts").get(Account.address == staker["address"])
    voted = participation[staker["address"]]
    claimed = claim_map[staker["address"]]

    if account_prev == None:
        # new staker, need to init his account
        inactive_windows = [] if voted else [window_index]

        return {
            "address": staker["address"],
            "vedough_balance": int(staker["balance"]),
            "slice_amount": 0,
            "state": state(voted, inactive_windows),
            "inactive_windows": inactive_windows,
        }
    else:
        inactive_windows = (
            account_prev["inactive_windows"]
            if voted
            else account_prev["inactive_windows"] + [window_index]
        )

        return {
            "address": staker["address"],
            "vedough_balance": int(staker["balance"]),
            "slice_amount": 0 if claimed else account_prev["slice_amount"],
            "state": state(voted, inactive_windows),
            "inactive_windows": inactive_windows,
        }


def update_account_with_distribution(account, rewards):
    if account["state"] == AccountState.SLASHED.value:
        account["slice_amount"] = 0
    else:
        account["slice_amount"] += rewards[account["address"]]

    return account
