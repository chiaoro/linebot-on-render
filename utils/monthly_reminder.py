# utils/monthly_reminder.py

import os, json, gspread
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv
from utils.line_push import push_text_to_group

load_dotenv()

# Google Sheets 認證
SCOPE = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds_dict = json.loads(os.getenv("GOOGLE_CREDENTIALS"))
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
gc = gspread.authorize(creds)

# 固定日期推播紀錄表
FIXED_PUSH_URL = "https://docs.google.com/spreadsheets/d/1FspUjkRckA1g4bYESb7QEUKl1FzOcL5BejhOqkMD0Po/edit"
fixed_sheet = gc.open_by_url(FIXED_PUSH_URL).worksheet("固定日期推播")

def send_monthly_fixed_reminders():
    today = datetime.now().strftime("%Y-%m-%d")

    data = fixed_sheet.get_all_records()
    for idx, record in enumerate(data, start=2):
        push_date = record.get("日期")
        message = record.get("推播項目")
        group = record.get("推播對象")
        status = record.get("提醒狀態")

        if push_date == today and status != "已推播":
            if group == "內科":
                group_id = os.getenv("internal_medicine_group_id")
            elif group == "外科":
                group_id = os.getenv("surgery_group_id")
            else:
                group_id = os.getenv("All_doctor_group_id")

            push_text_to_group(group_id, f"📣{message}")
            fixed_sheet.update_cell(idx, list(record.keys()).index("提醒狀態") + 1, "已推播")
