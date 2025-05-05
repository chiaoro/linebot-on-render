# utils/meeting_reminder.py

import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
from utils.line_push import push_text_to_user
from utils.gspread_client import get_gspread_client

load_dotenv()

RECORD_SHEET_URL = "https://docs.google.com/spreadsheets/d/1-mI71sC7TE-f8Gb9YPddhVGJrozKxLIdJlSBf2khJsA/edit"

def send_meeting_reminder():
    gc = get_gspread_client()
    sheet = gc.open_by_url(RECORD_SHEET_URL).worksheet("院務會議請假")

    today = datetime.now().date()
    target_date = today + timedelta(days=3)
    target_str = target_date.strftime("%Y-%m-%d")

    push_text_to_user(
        user_id=os.getenv("All_doctor_group_id"),
        text=f"📣【院務會議提醒】\n三天後({target_str})將召開院務會議，請大家確認是否出席唷！"
    )
