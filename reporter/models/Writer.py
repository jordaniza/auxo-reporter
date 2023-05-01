import json, csv
from pathlib import Path
from dataclasses import dataclass
from typing import Any

from reporter.models.Config import Config


@dataclass
class Writer:
    config: Config

    @property
    def path(self) -> str:
        return f"reports/{self.config.date}"

    @property
    def csv_path(self) -> str:
        return f"{self.path}/csv"

    @property
    def json_path(self) -> str:
        return f"{self.path}/json"

    @staticmethod
    def flatten_json(y):
        out = {}

        def flatten(x, name=""):
            # If the Nested key-value
            # pair is of dict type
            if type(x) is dict:
                for a in x:
                    flatten(x[a], name + a + "_")

            # If the Nested key-value
            # pair is of list type
            elif type(x) is list:
                i = 0
                for a in x:
                    flatten(a, name + str(i) + "_")
                    i += 1
            else:
                out[name[:-1]] = x

        flatten(y)
        return out

    def flatten_json_array(self, data):
        out = []
        for item in data:
            out.append(self.flatten_json(item))
        return out

    @staticmethod
    def write_csv(data, path: str, fieldnames: list[str]) -> None:
        with open(path, "w+", newline="") as f:
            writer = csv.writer(f, delimiter=",")
            writer.writerow(fieldnames)

            for row in data:
                if not isinstance(row, dict):
                    writer.writerow([row])
                    continue
                flattened_row = []
                for _, v in row.items():
                    if isinstance(v, dict):
                        for __, sub_v in v.items():
                            flattened_row.append(sub_v)
                    else:
                        flattened_row.append(v)
                writer.writerow(flattened_row)

    # create the directory in the reports folder for csv and json if it doesn't exist
    def _create_dir(self) -> None:
        Path(self.path).mkdir(parents=True, exist_ok=True)
        Path(self.csv_path).mkdir(parents=True, exist_ok=True)
        Path(self.json_path).mkdir(parents=True, exist_ok=True)

    # write to a csv file
    def to_csv(self, data, name: str, fieldnames: list[str]) -> None:
        self._create_dir()
        self.write_csv(data, f"{self.csv_path}/{name}.csv", fieldnames)

    # write to a json file
    def to_json(self, data, name: str) -> None:
        self._create_dir()
        with open(f"{self.json_path}/{name}.json", "w") as f:
            json.dump(data, f, indent=4)

    def to_csv_and_json(self, data, name: str) -> None:
        if isinstance(data, list):
            csv_data = self.flatten_json_array(data)
            if len(csv_data) > 0:
                keys = csv_data[0].keys()
            else:
                keys = []
        else:
            csv_data = self.flatten_json(data)
            keys = csv_data.keys()
            csv_data = [csv_data]
        self.to_json(data, name)
        self.to_csv(csv_data, name, keys)

    def list_to_csv_and_json(self, data, name: str) -> None:
        self.to_csv([v for v in data], name, [name])
        self.to_json([v for v in data], name)

    def lists_to_csv_and_json(self, lists: list[tuple[str, list[Any]]]) -> None:
        for name, ls in lists:
            self.list_to_csv_and_json(ls, name)
