# utils/meeting_leave_scheduler.py

import os, json, gspread
from dotenv import load_dotenv
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
from utils.line_push_utils import push_text_to_user

load_dotenv()

# ✅ Google Sheets 認證
SCOPE = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds_dict = json.loads(os.getenv("GOOGLE_CREDENTIALS"))
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
gc = gspread.authorize(creds)

# ✅ 院務會議請假記錄表
RECORD_SHEET_URL = "https://docs.google.com/spreadsheets/d/1-mI71sC7TE-f8Gb9YPddhVGJrozKxLIdJlSBf2khJsA/edit"

# ✅ 群組 ID（推播對象）
GROUP_ID = os.getenv("All_doctor_group_id")

def run_meeting_leave_scheduler():
    """每天早上檢查三天後是否有院務會議，並提醒所有醫師回覆"""
    sheet = gc.open_by_url(RECORD_SHEET_URL).worksheet("院務會議請假")
    today = datetime.now().date()
    target_date = today + timedelta(days=3)

    # 推播提醒（簡單提醒三天後開會）
    text = f"📣【院務會議提醒】\n請注意！三天後 ({target_date.strftime('%Y/%m/%d')}) 有院務會議，請儘速填寫出席或請假回覆。"
    push_text_to_user(GROUP_ID, text)
