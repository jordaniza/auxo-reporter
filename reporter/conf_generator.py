from pathlib import Path
from typing_extensions import TypedDict
from reporter.helpers import get_dates

import json


class Config(TypedDict):
    date: str
    start_timestamp: int
    end_timestamp: int
    block_snapshot: int
    distribution_window: int
    slice_to_distribute: str


def create_conf() -> Config:
    (date, start_date, end_date) = get_dates()

    block_snapshot = int(input("🔗 What is snapshot block? "))

    distribution_window = int(input("#️⃣  What is the distribution window? "))

    slice_to_distribute = input("🤑 What is the number of SLICE units to distribute? ")

    return {
        "date": f"{date.year}-{date.month}",
        "start_timestamp": int(start_date.timestamp()),
        "end_timestamp": int(end_date.timestamp()),
        "block_snapshot": block_snapshot,
        "distribution_window": distribution_window,
        "slice_to_distribute": slice_to_distribute,
    }


def gen():
    conf = create_conf()

    path = f"reports/{conf['date']}"

    Path(path).mkdir(parents=True, exist_ok=True)
    Path(f"{path}/csv/").mkdir(parents=True, exist_ok=True)
    Path(f"{path}/json/").mkdir(parents=True, exist_ok=True)

    conf_json_file = open(f"{path}/epoch-conf.json", "w+")
    conf_json_file.write(json.dumps(conf, indent=4))
