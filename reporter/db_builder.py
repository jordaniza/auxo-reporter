from helpers import get_db
from decimal import Decimal
from queries import get_stakers, get_votes, get_claimed_for_window
from account import (
    AccountState,
    init_account,
    update_account_with_distribution,
    to_staker,
)

import json
import datetime
import itertools
import functools


def write_governance_stats(db, stakers, votes, proposals, voters, non_voters):
    db.table("governance_stats").insert(
        {
            "stakers": list(map(to_staker, stakers)),
            "votes": votes,
            "proposals": proposals,
            "voters": voters,
            "non_voters": non_voters,
        },
    )


def write_accounts_and_distribution(db, accounts, distribution):
    db.table("accounts").insert_multiple(accounts)
    db.table("distribution").insert_multiple(distribution)


def filter_slashed(accounts):
    slashed = list(filter(lambda a: a["state"] == AccountState.SLASHED.value, accounts))
    amount = functools.reduce(lambda acc, a: acc + a["slice_amount"], slashed, 0)
    return (slashed, amount)


def distribute(account, pro_rata):
    reward = {"address": account["address"], "amount": 0}

    if account["state"] != AccountState.SLASHED.value:
        reward["amount"] = int(
            Decimal(pro_rata * account["vedough_balance"]) / Decimal(1e18)
        )

    return reward


def compute_distribution(conf, accounts):
    slice_units = Decimal(int(Decimal(conf["slice_to_distribute"]) * Decimal(1e18)))

    # `filter_slashed` is computing slashed accounts and total slashed slices (`slashed_amount`)
    (slashed, slashed_amount) = filter_slashed(accounts)

    # increase slice units to account for slashed and ridistribution
    slice_units += slashed_amount

    # take into account only NOT slashed accounts
    accounts_for_distro = filter(lambda a: a not in slashed, accounts)
    total_supply = functools.reduce(
        lambda s, a: s + a["vedough_balance"], accounts_for_distro, Decimal(0)
    )

    # compute prorata
    pro_rata = Decimal(slice_units * Decimal(1e18) / total_supply)

    distribution = list(map(distribute, accounts, itertools.repeat(pro_rata)))

    # least rewarded account gets the reminder
    least_rewarded = min(filter(lambda a: a['amount'] > 0, distribution), key=lambda a: a['amount'])
    least_rewarded['amount'] += int(slice_units - functools.reduce(lambda acc, a: acc + a['amount'], distribution, 0))

    return distribution


def build(path, prev_path):
    epoch_conf = json.load(open(f"{path}/epoch-conf.json"))

    db = get_db(path, drop=True)
    db_prev = get_db(prev_path)

    start_date = datetime.date.fromtimestamp(epoch_conf["start_timestamp"])
    end_date = datetime.date.fromtimestamp(epoch_conf["end_timestamp"])
    print(f"⚗ Building database from {start_date} to {end_date}...")

    # get stakers and misc governance stats
    stakers = get_stakers(epoch_conf)
    (votes, proposals, voters, non_voters) = get_votes(epoch_conf, stakers)
    claimed_addrs = get_claimed_for_window(epoch_conf["distribution_window"] - 1)

    write_governance_stats(db, stakers, votes, proposals, voters, non_voters)

    # participation mapping (address -> voted?)
    participation = {addr: (lambda x: x in voters)(addr) for (addr, _) in stakers}

    # claimed mapping (address -> claimed?)
    claimed_map = {addr: (lambda x: x in claimed_addrs)(addr) for (addr, _) in stakers}

    # compute users' initial state for this epoch
    # this step has two purposes:
    #  - creating a delta for slice_amounts (for unclaimed and freezed)
    #  - flagging users as active/inactive/slashed
    accounts = list(
        map(
            init_account,
            map(to_staker, stakers),  # all the stakers
            itertools.repeat(db_prev),  # prev accounts
            itertools.repeat(epoch_conf["distribution_window"]),  # distribution window
            itertools.repeat(participation),  # participation
            itertools.repeat(claimed_map),  # claimed
        )
    )

    # compute distribution given configuration file and accounts state
    # `compute_distribution` will also update `account.slice_amount` for each account
    distribution = compute_distribution(epoch_conf, accounts)
    distribution_map = {distr["address"]: distr["amount"] for distr in distribution}

    accounts = map(
        update_account_with_distribution,
        accounts,
        itertools.repeat(distribution_map),
    )

    write_accounts_and_distribution(db, accounts, distribution)
