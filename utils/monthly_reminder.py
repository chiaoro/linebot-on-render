# utils/monthly_reminder.py

from utils.line_push import push_text_to_user
import gspread
import os, json
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

SCOPE = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds_dict = json.loads(os.getenv("GOOGLE_CREDENTIALS", "{}"))
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
gc = gspread.authorize(creds)

def send_monthly_fixed_reminders():
    today = datetime.now().strftime("%Y-%m-%d")

    # 自動推播固定日子提醒（例：5/1 夜點費開啟填寫）
    push_text_to_user(
        user_id=os.getenv("All_doctor_group_id"),
        text=f"📣【提醒】今天是{today}，請記得填寫夜點費資料！"
    )
