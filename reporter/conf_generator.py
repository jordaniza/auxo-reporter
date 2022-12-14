from pathlib import Path
from pydantic import BaseModel, parse_file_as
from reporter.helpers import get_dates
import json
from typing import Optional


class RewardToken(BaseModel):
    amount: str
    token: str
    decimals: int


class Config(BaseModel):
    date: str
    start_timestamp: int
    end_timestamp: int
    block_snapshot: int
    distribution_window: int
    rewards: list[RewardToken]


def parse_rewards() -> list[RewardToken]:
    file = input("🤑 Path to the Rewards JSON file ")
    return parse_file_as(list[RewardToken], path=file)


def create_conf() -> Config:
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
    return parse_file_as(Config, path=f"{config_path}/epoch-conf.json")


def gen():
    conf = create_conf()

    path = f"reports/{conf.date}"

    Path(path).mkdir(parents=True, exist_ok=True)
    Path(f"{path}/csv/").mkdir(parents=True, exist_ok=True)
    Path(f"{path}/json/").mkdir(parents=True, exist_ok=True)

    with open(f"{path}/epoch-conf.json", "w+") as j:
        j.write(json.dumps(conf.dict(), indent=4))
