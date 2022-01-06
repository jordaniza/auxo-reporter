import csv
import json
import calendar
import datetime

def yes_or_no(question):
    while "the answer is invalid":
        reply = str(input(f'{question} [y/n]: ')).lower().strip()
        if reply[:1] == 'y':
            return True
        if reply[:1] == 'n':
            return False

def get_timestamps(month, year):
    (_, n_days) = calendar.monthrange(year, month)

    date = datetime.date(year, month, 1)
    start_date = datetime.datetime(year, month, 1, 0, 0, 0)
    end_date = datetime.datetime(year, month, n_days, 23, 59, 59)

    return (date, start_date, end_date)

## writers

def write_csv(data, path, fieldnames):
    with open(path, 'w+') as f:
        writer = csv.DictWriter(f, delimiter=',', fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)

def write_json(data, path):
    with open(path, 'w+') as f:
        data_json = json.dumps(data, indent=4)
        f.write(data_json)