from typing import TypeVar
from tinydb import TinyDB
from reporter.types import Account, AccountState

# python insantiates generics separate to function definition
T = TypeVar("T")


def unique(ls: list[T]) -> list[T]:
    """Remove duplicates from a list"""
    return list(set(ls))


def yes_or_no(question: str):
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


def filter_state(accounts: list[Account], state: AccountState) -> list[Account]:
    """Return all accounts in list of accounts with specific state"""
    return list(filter(lambda a: a.state == state, accounts))


def get_db(db_path, drop=False):
    """
    Get or instantiate existing tinyDB instance. Pass drop to clear.
    """
    db = TinyDB(f"{db_path}/reporter-db.json")

    if drop:
        db.drop_tables()

    return db
