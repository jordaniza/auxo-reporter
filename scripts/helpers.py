import calendar
import datetime

def yes_or_no(question):
    while "the answer is invalid":
        reply = str(input(f'{question} [y/n]: ')).lower().strip()
        if reply[:1] == 'y':
            return True
        if reply[:1] == 'n':
            return False

def get_timestamps(month):
    today = datetime.date.today()
    (_, n_days) = calendar.monthrange(today.year, month)

    date = datetime.date(today.year, month, 1)
    start_date = datetime.datetime(today.year, month, 1, 0, 0, 0)
    end_date = datetime.datetime(today.year, month, n_days, 23, 59, 59)

    return (date, start_date, end_date)
