# utils/meeting_reminder.py

import os, json, gspread
from datetime import datetime, timedelta
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv
from utils.line_push import push_text_to_user

load_dotenv()

# Google Sheets 認證
SCOPE = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds_dict = json.loads(os.getenv("GOOGLE_CREDENTIALS"))
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
gc = gspread.authorize(creds)

# 開啟院務會議請假記錄表
RECORD_SHEET_URL = "https://docs.google.com/spreadsheets/d/1-mI71sC7TE-f8Gb9YPddhVGJrozKxLIdJlSBf2khJsA/edit"
record_sheet = gc.open_by_url(RECORD_SHEET_URL).worksheet("院務會議請假")

def send_meeting_reminder():
    today = datetime.now().date()
    target_date = today + timedelta(days=3)  # 三天後的會議
    target_str = target_date.strftime("%Y-%m-%d")

    # 這邊可以自訂要推播的內容
    push_text_to_user(
        user_id=os.getenv("All_doctor_group_id"),
        text=f"📣【院務會議提醒】\n三天後({target_str})將召開院務會議，請大家確認是否出席唷！"
    )
