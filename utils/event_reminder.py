# utils/event_reminder.py

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

# 重要會議提醒表
EVENT_SHEET_URL = "https://docs.google.com/spreadsheets/d/1FspUjkRckA1g4bYESb7QEUKl1FzOcL5BejhOqkMD0Po/edit"
event_sheet = gc.open_by_url(EVENT_SHEET_URL).worksheet("固定日期推播")

def send_important_event_reminder():
    today = datetime.now()
    tomorrow = today + datetime.timedelta(days=1)
    tomorrow_str = tomorrow.strftime("%Y-%m-%d")

    records = event_sheet.get_all_records()

    for idx, rec in enumerate(records, start=2):
        meeting_date = rec.get("日期")
        meeting_name = rec.get("推播項目")
        group = rec.get("推播對象")
        status = rec.get("提醒狀態")

        if meeting_date == tomorrow_str and status != "已推播":
            weekday = "一二三四五六日"[tomorrow.weekday()]
            message = f"📣【重要會議提醒】\n明天({tomorrow_str})（星期{weekday}）即將召開 {meeting_name}，請各位準時出席唷。"

            if group == "內科":
                group_id = os.getenv("internal_medicine_group_id")
            elif group == "外科":
                group_id = os.getenv("surgery_group_id")
            else:
                group_id = os.getenv("All_doctor_group_id")

            push_text_to_group(group_id, message)
            event_sheet.update_cell(idx, list(rec.keys()).index("提醒狀態") + 1, "已推播")
