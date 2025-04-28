# utils/monthly_reminder.py

import os
import json
import gspread
from dotenv import load_dotenv
from oauth2client.service_account import ServiceAccountCredentials
from utils.line_push import push_text_to_user
from datetime import datetime

load_dotenv()

# Google Sheets認證
SCOPE = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds_dict = json.loads(os.getenv("GOOGLE_CREDENTIALS", "{}"))
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
gc = gspread.authorize(creds)

def send_monthly_fixed_reminders():
    today = datetime.now().strftime("%Y-%m-%d")
    
    # 發送固定每月提醒
    push_text_to_user(
        user_id=os.getenv("All_doctor_group_id"),
        text=f"📅【固定日期提醒】\n今天是 {today}，請記得依照既定事項完成唷～"
    )
