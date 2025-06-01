# utils/date_parser.py

import re

def parse_dates_from_text(text):
    dates = []
    parts = re.split(r"[、,，\s]+", text)
    for part in parts:
        if "-" in part:
            try:
                start, end = part.split("-")
                m = int(start.split("/")[0])
                start_day = int(start.split("/")[1])
                end_day = int(end.split("/")[1])
                for d in range(start_day, end_day + 1):
                    dates.append(f"{m}/{d}")
            except:
                continue
        else:
            dates.append(part.strip())
    return dates


def expand_date_range(text):
    dates = []
    parts = re.split(r"[、,，\s]+", text)
    for part in parts:
        if "-" in part:
            try:
                start, end = part.split("-")
                m = int(start.split("/")[0])
                start_day = int(start.split("/")[1])
                end_day = int(end.split("/")[1])
                for d in range(start_day, end_day + 1):
                    dates.append(f"{m}/{d}")
            except:
                continue
        else:
            dates.append(part.strip())
    return dates
