# utils/date_utils.py
from datetime import datetime, timedelta
import re

def expand_date_range(date_str: str) -> list:
    """將 4/15-17 或 4/15、4/17 類型日期字串展開為 ['4/15', '4/16', '4/17']"""
    today_year = datetime.now().year
    results = []

    parts = re.split(r"[、,]", date_str)

    for part in parts:
        part = part.strip()

        if "-" in part:
            start_str, end_str = part.split("-")
            if "/" not in end_str:
                start_month = int(start_str.split("/")[0])
                start_day = int(start_str.split("/")[1])
                end_day = int(end_str)
                end_month = start_month
            else:
                start_month, start_day = map(int, start_str.split("/"))
                end_month, end_day = map(int, end_str.split("/"))

            start_date = datetime(today_year, start_month, start_day)
            end_date = datetime(today_year, end_month, end_day)

            while start_date <= end_date:
                results.append(start_date.strftime("%-m/%-d"))
                start_date += timedelta(days=1)
        else:
            results.append(part)

    return results
