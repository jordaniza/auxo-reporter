from tinydb import TinyDB

import csv
import json
import calendar
import datetime


# get_db


def get_db(db_path, drop=False):
    db = TinyDB(f"{db_path}/reporter-db.json")

    if drop:
        db.drop_tables()

    return db


# misc


def yes_or_no(question):
    while "the answer is invalid":
        reply = str(input(f"{question} [y/n]: ")).lower().strip()
        if reply[:1] == "y":
            return True
        if reply[:1] == "n":
            return False


def get_dates():
    date = input("📆 What epoch? [month-year, {1-12}-{year}]: ")
    [month, year] = [int(token) for token in date.split("-")]

    (_, n_days) = calendar.monthrange(year, month)

    date = datetime.date(year, month, 1)
    start_date = datetime.datetime(year, month, 1, 0, 0, 0)
    end_date = datetime.datetime(year, month, n_days, 23, 59, 59)

    return (date, start_date, end_date)


## writers
