import os, json
import pytest
from reporter.models import Config, Writer


def test_write_claims(monkeypatch, config: Config):
    # monkeypatch.setattr("reporter.writer.load_conf", lambda path: config)

    # path = "reporter/test/stubs/db"
    # main(path)
    pass


# tmp_path is an inbuilt pytest fixture
# it uses python's Pathlib to create a temporary directory
@pytest.fixture(scope="function")
def tmp_dir(tmp_path):
    tmp_dir = tmp_path / "2099-12"
    tmp_dir.mkdir()
    yield
    tmp_dir.rmdir()


@pytest.fixture
def writer(config):
    config.date = "2099-12"
    return Writer(config)


def test_create_dirs(writer):
    writer._create_dir()
    assert os.path.exists(writer.path)
    assert os.path.exists(writer.csv_path)
    assert os.path.exists(writer.json_path)


@pytest.mark.parametrize(
    "data, assert_csv",
    [
        [
            [
                {"key1": 1, "key2": 2},
                {"key1": 3, "key2": 4},
            ],
            "key1,key2\n1,2\n3,4\n",
        ],
        [
            {
                "key1": 1,
                "key2": 2,
            },
            "key1,key2\n1,2\n",
        ],
    ],
)
def test_write_csv_and_json(tmp_dir, writer, data, assert_csv):

    # Write data to CSV and JSON files
    writer.to_csv_and_json(data=data, name="test")

    # Read the CSV file
    with open(f"{writer.csv_path}/test.csv", "r") as f:
        csv_data = f.read()
    assert csv_data == assert_csv

    # Read the JSON file
    with open(f"{writer.json_path}/test.json", "r") as f:
        json_data = json.load(f)
    assert json_data == data
