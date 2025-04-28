# utils/night_shift_fee_reminder.py

import os, json
from datetime import datetime, date
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from utils.line_push import push_text_to_group

# Google Sheets認證
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = json.loads(os.getenv("GOOGLE_CREDENTIALS", "{}"))
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
gc = gspread.authorize(creds)

# 環境變數
REMINDER_SHEET_URL = os.getenv("REMINDER_SHEET_URL")  # 夜點費提醒名冊
GROUP_ID = os.getenv("surgery_group_id") or os.getenv("All_doctor_group_id")

def daily_night_fee_reminder():
    today = date.today()
    if not (1 <= today.day <= 5):
        return

    if not REMINDER_SHEET_URL:
        print("❌ REMINDER_SHEET_URL 環境變數未設定！")
        return

    sheet = gc.open_by_url(REMINDER_SHEET_URL).sheet1
    records = sheet.get_all_records()

    for idx, rec in enumerate(records, start=2):
        doctor = rec.get("醫師姓名")
        status = rec.get("提醒狀態", "")

        if not doctor:
            continue

        if status != "已提醒":
            message = f"📌 {doctor} 醫師，請於本月 1～5 號內繳交夜點費資料！"
            push_text_to_group(GROUP_ID, message)
            sheet.update_cell(idx, list(records[0].keys()).index("提醒狀態") + 1, "已提醒")
