# utils/event_reminder.py

import os
import json
import gspread
from dotenv import load_dotenv
from oauth2client.service_account import ServiceAccountCredentials
from utils.line_push import push_text_to_user
from datetime import datetime, timedelta

load_dotenv()

# Google Sheets認證
SCOPE = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds_dict = json.loads(os.getenv("GOOGLE_CREDENTIALS", "{}"))
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
gc = gspread.authorize(creds)

def send_important_event_reminder():
    tomorrow = datetime.now() + timedelta(days=1)
    tomorrow_str = tomorrow.strftime("%Y-%m-%d")
    
    # 發送重要會議前一天提醒
    push_text_to_user(
        user_id=os.getenv("All_doctor_group_id"),
        text=f"📣【重要會議提醒】\n明天 ({tomorrow_str}) 有重要院務會議，請大家準時出席！"
    )
