from pathlib import Path
from helpers import get_dates

import json


def gen():
    (date, start_date, end_date) = get_dates()

    block_snapshot = int(input("🔗 What is snapshot block? "))

    distribution_window = int(input("#️⃣  What is the distribution window? "))

    slice_to_distribute = input("🤑 What is the number of SLICE units to distribute? ")

    conf = {
        "date": f"{date.year}-{date.month}",
        "start_timestamp": int(start_date.timestamp()),
        "end_timestamp": int(end_date.timestamp()),
        "block_snapshot": block_snapshot,
        "distribution_window": distribution_window,
        "slice_to_distribute": slice_to_distribute,
    }

    path = f"reports/{date.year}-{date.month}"

    Path(path).mkdir(parents=True, exist_ok=True)
    Path(f"{path}/csv/").mkdir(parents=True, exist_ok=True)
    Path(f"{path}/json/").mkdir(parents=True, exist_ok=True)

    conf_json_file = open(f"{path}/epoch-conf.json", "w+")
    conf_json_file.write(json.dumps(conf, indent=4))
