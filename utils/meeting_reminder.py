# utils/meeting_reminder.py

import os
import json
import gspread
from dotenv import load_dotenv
from oauth2client.service_account import ServiceAccountCredentials
from utils.line_push import push_text_to_user
from datetime import datetime, timedelta
from utils.gspread_client import get_gspread_client



load_dotenv()

# Google Sheets 認證
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
CREDS_DICT = json.loads(os.getenv("GOOGLE_CREDENTIALS"))
CREDS = ServiceAccountCredentials.from_json_keyfile_dict(CREDS_DICT, SCOPE)
GC = gspread.authorize(CREDS)

# 院務會議請假紀錄表
RECORD_SHEET_URL = "https://docs.google.com/spreadsheets/d/1-mI71sC7TE-f8Gb9YPddhVGJrozKxLIdJlSBf2khJsA/edit"
record_sheet = GC.open_by_url(RECORD_SHEET_URL).worksheet("院務會議請假")

def send_meeting_reminder():
    today = datetime.now().date()
    target_date = today + timedelta(days=3)  # 3天後的會議提醒
    target_str = target_date.strftime("%Y-%m-%d")

    # 推播到群組
    push_text_to_user(
        user_id=os.getenv("All_doctor_group_id"),
        text=f"📣【院務會議提醒】\n三天後({target_str})將召開院務會議，請大家確認是否出席唷！"
    )



