from pathlib import Path
from pydantic import parse_file_as
import json
import calendar
import datetime

from reporter.types import Config, Reward


def get_dates():
    """Parse an input in format `f"{date.year}-{date.month}"` to datetimes"""
    date = input("📆 What epoch? [month-year, {1-12}-{year}]: ")
    [month, year] = [int(token) for token in date.split("-")]

    (_, n_days) = calendar.monthrange(year, month)

    date = datetime.date(year, month, 1)
    start_date = datetime.datetime(year, month, 1, 0, 0, 0)
    end_date = datetime.datetime(year, month, n_days, 23, 59, 59)

    return (date, start_date, end_date)


def parse_rewards() -> list[Reward]:
    """Ingests a JSON file of rewards into a list of Reward Objects"""
    file = input("🤑 Path to the Rewards JSON file ")
    return parse_file_as(list[Reward], path=file)


def create_conf() -> Config:
    """Generates the base config object from user input"""
    (date, start_date, end_date) = get_dates()
    rewards = parse_rewards()
    block_snapshot = int(input("🔗 What is snapshot block? "))
    distribution_window = int(input("#️⃣ What is the distribution window? "))

    return Config(
        date=f"{date.year}-{date.month}",
        start_timestamp=int(start_date.timestamp()),
        end_timestamp=int(end_date.timestamp()),
        block_snapshot=block_snapshot,
        distribution_window=distribution_window,
        rewards=rewards,
    )


def load_conf(config_path: str) -> Config:
    """Loads an existing config from file"""
    return parse_file_as(Config, path=f"{config_path}/epoch-conf.json")


def main():
    """Generates config file and saves in newly created directory with correct strcutre"""
    conf = create_conf()

    # create directories
    path = f"reports/{conf.date}"
    Path(path).mkdir(parents=True, exist_ok=True)
    Path(f"{path}/csv/").mkdir(parents=True, exist_ok=True)
    Path(f"{path}/json/").mkdir(parents=True, exist_ok=True)

    # write new config file
    with open(f"{path}/epoch-conf.json", "w+") as j:
        j.write(json.dumps(conf.dict(), indent=4))
