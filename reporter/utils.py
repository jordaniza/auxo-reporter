import csv
import json
from typing import Any, TypeVar
from reporter.models import Account, AccountState

# python insantiates generics separate to function definition
T = TypeVar("T")


def unique(ls: list[T]) -> list[T]:
    """Remove duplicates from a list"""
    return list(set(ls))


def yes_or_no(question: str) -> bool:
    """
    Require y or n (case insenstive) as answer to `question`.
    Defaults to N with no response
    """
    while "the answer is invalid":
        reply = input(f"{question} [y/N]: ")
        if not reply:
            return False
        reply = str(reply).lower().strip()
        if reply[:1] == "y":
            return True
        if reply[:1] == "n":
            return False
    return False


def filter_state(accounts: list[Account], state: AccountState) -> list[Account]:
    """Return all accounts in list of accounts with specific state"""
    return list(filter(lambda a: a.state == state, accounts))


def write_csv(data: Any, path: str, fieldnames: list[str]) -> None:
    with open(path, "w+") as f:
        writer = csv.DictWriter(
            f, delimiter=",", fieldnames=fieldnames, extrasaction="ignore"
        )
        writer.writeheader()
        if isinstance(data, list):
            writer.writerows(data)
        else:
            writer.writerow(data)


def write_list_csv(data: Any, path: str, fieldname: str) -> None:
    new_data = [{fieldname: d} for d in data]
    write_csv(new_data, path, [fieldname])


def write_json(data: Any, path: str) -> None:
    with open(path, "w+") as f:
        data_json = json.dumps(data, indent=4)
        f.write(data_json)
