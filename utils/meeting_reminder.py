# utils/meeting_reminder.py

from utils.line_push import push_text_to_user
import gspread
import os, json
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

# Google Sheets認證
SCOPE = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds_dict = json.loads(os.getenv("GOOGLE_CREDENTIALS", "{}"))
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
gc = gspread.authorize(creds)

# 開啟院務會議請假記錄表
RECORD_SHEET_URL = os.getenv("RECORD_SHEET_URL")  # 你的試算表網址
record_sheet = gc.open_by_url(RECORD_SHEET_URL).worksheet("院務會議請假")

def send_meeting_reminder():
    today = datetime.now().date()
    target_date = today + timedelta(days=3)  # 例：三天後的會議
    target_str = target_date.strftime("%Y-%m-%d")

    # 這裡可以讀取表格，找出還沒回覆的人名
    # 也可以直接推播提醒大家有會議

    push_text_to_user(
        user_id=os.getenv("All_doctor_group_id"),  # 這裡記得用你的群組id
        text=f"📣【院務會議提醒】\n三天後({target_str})將召開院務會議，請大家確認是否出席唷！"
    )
