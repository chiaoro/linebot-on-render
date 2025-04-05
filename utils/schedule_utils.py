import os
from datetime import datetime
from utils.google_auth import get_gspread_client
from utils.line_push import push_text_to_user

# 設定
form_url = os.getenv("FORM_URL")

def send_form_to_all_users():
    gc = get_gspread_client()
    sheet = gc.open_by_url(os.getenv("FORM_RESPONSES_SHEET_URL")).worksheet("line_users")
    users = sheet.get_all_values()[1:]
    for user_id, name in users:
        msg = f"{name} 醫師您好，請填寫下個月休假登記表單：\n{form_url}"
        push_text_to_user(user_id, msg)

def check_unsubmitted():
    gc = get_gspread_client()
    response_sheet = gc.open_by_url(os.getenv("FORM_RESPONSES_SHEET_URL")).sheet1
    bind_sheet = gc.open_by_url(os.getenv("FORM_RESPONSES_SHEET_URL")).worksheet("line_users")

    submitted_names = [row[1] for row in response_sheet.get_all_values()[1:] if row[1]]
    all_users = bind_sheet.get_all_values()[1:]
    unsubmitted = [name for uid, name in all_users if name not in submitted_names]

    # 回報名單
    if unsubmitted:
        msg = "以下醫師尚未填寫表單：\n" + "\n".join(unsubmitted)
    else:
        msg = "✅ 所有醫師皆已填寫完畢！"
    # 推播給管理員（請填上你的 LINE User ID）
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
    import re
    gc = get_gspread_client()
    sched = gc.open_by_url(os.getenv("DOCTOR_SCHEDULE_SHEET_URL")).sheet1
    # 解析 like "5/10-12,15,18-20"
    days = []
    for part in re.split(r"[，,]", off_text):
        part = part.strip()
        if "-" in part:
            start, end = part.replace("5/", "").split("-")
            days += list(range(int(start), int(end)+1))
        elif part:
            days.append(int(part))

    row = [name]
    headers = sched.row_values(1)
    for col in headers[1:]:
        try:
            day = int(col)
            row.append("off" if day in days else "")
        except:
            row.append("")
    sched.append_row(row)
