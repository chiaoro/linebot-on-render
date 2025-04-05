import os
import re
from datetime import datetime
from utils.google_auth import get_gspread_client
from utils.line_push import push_text_to_user




def handle_submission(name, off_text):
    gc = get_gspread_client()
    sched = gc.open_by_url(os.getenv("DOCTOR_SCHEDULE_SHEET_URL")).sheet1

    headers = sched.row_values(1)
    date_cols = {int(day): idx for idx, day in enumerate(headers[1:], start=2) if day.isdigit()}

    raw_parts = re.split(r"[，,\s\n]+", off_text)
    days = set()
    for part in raw_parts:
        part = part.strip().replace("5/", "").replace("05/", "")
        if "-" in part:
            try:
                start, end = map(int, part.split("-"))
                days.update(range(start, end + 1))
            except:
                continue
        elif part.isdigit():
            days.add(int(part))

    existing = sched.get_all_values()
    name_col = [row[0] for row in existing]
    if name in name_col:
        row_idx = name_col.index(name) + 1
        row_data = sched.row_values(row_idx)
        for d in days:
            if d in date_cols:
                col_idx = date_cols[d]
                if len(row_data) < col_idx or row_data[col_idx - 1] == "":
                    sched.update_cell(row_idx, col_idx, "off")
    else:
        new_row = [name] + ["" for _ in range(len(headers) - 1)]
        for d in days:
            if d in date_cols:
                new_row[date_cols[d] - 1] = "off"
        sched.append_row(new_row)
