import os
import re
from datetime import datetime
from utils.google_auth import get_gspread_client
from utils.line_push import push_text_to_user

form_url = os.getenv("FORM_URL")



def check_unsubmitted():
    gc = get_gspread_client()
    response_sheet = gc.open_by_url(os.getenv("FORM_RESPONSES_SHEET_URL")).sheet1
    bind_sheet = gc.open_by_url(os.getenv("FORM_RESPONSES_SHEET_URL")).worksheet("line_users")

    submitted_names = [row[1] for row in response_sheet.get_all_values()[1:] if row[1]]
    all_users = bind_sheet.get_all_values()[1:]
    unsubmitted = [name for uid, name in all_users if name not in submitted_names]

    if unsubmitted:
        msg = "以下醫師尚未填寫表單：\n" + "\n".join(unsubmitted)
    else:
        msg = "✅ 所有醫師皆已填寫完畢！"

    push_text_to_user("你的LINE_USER_ID", msg)

def remind_unsubmitted():
    today = datetime.now()
    if today.day < 10:
        return
    gc = get_gspread_client()
    response_sheet = gc.open_by_url(os.getenv("FORM_RESPONSES_SHEET_URL")).sheet1
    bind_sheet = gc.open_by_url(os.getenv("FORM_RESPONSES_SHEET_URL")).worksheet("line_users")

    submitted_names = [row[1] for row in response_sheet.get_all_values()[1:] if row[1]]
    all_users = bind_sheet.get_all_values()[1:]
    for uid, name in all_users:
        if name not in submitted_names:
            msg = f"{name} 醫師提醒您：請盡快填寫表單，謝謝您！\n{form_url}"
            push_text_to_user(uid, msg)

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
