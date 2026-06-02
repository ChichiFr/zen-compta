from datetime import date


def month_start(value: date) -> date:
    return date(value.year, value.month, 1)


def next_month_start(value: date) -> date:
    if value.month == 12:
        return date(value.year + 1, 1, 1)
    return date(value.year, value.month + 1, 1)
