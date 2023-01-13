import csv, json, os
from typing import TypeVar, Any
from tinydb import TinyDB
from dotenv import load_dotenv

from reporter.types import Account, AccountState
from errors import MissingEnvironmentVariableException


# python insantiates generics separate to function definition
T = TypeVar("T")


def env_var(accessor: str) -> str:
    load_dotenv()

    var = os.environ.get(accessor)
    if not var:
        raise MissingEnvironmentVariableException(accessor)
    return var


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


def get_db(db_path: str, drop=False) -> TinyDB:
    """
    Get or instantiate existing tinyDB instance. Pass drop to clear.
    """
    db = TinyDB(
        f"{db_path}/reporter-db.json",
        indent=4,
    )

    if drop:
        db.drop_tables()

    return db


def write_csv(data: Any, path: str, fieldnames: list[str]) -> None:
    with open(path, "w+") as f:
        writer = csv.DictWriter(f, delimiter=",", fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)


def write_list_csv(data: Any, path: str, fieldname: str) -> None:
    new_data = [{fieldname: d} for d in data]
    write_csv(new_data, path, [fieldname])


def write_json(data: Any, path: str) -> None:
    with open(path, "w+") as f:
        data_json = json.dumps(data, indent=4)
        f.write(data_json)
