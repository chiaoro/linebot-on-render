# utils/event_reminder.py

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

def send_important_event_reminder():
    # 今天要推播明天的重要會議
    today = datetime.now()
    tomorrow = today + timedelta(days=1)
    tomorrow_str = tomorrow.strftime("%Y-%m-%d")

    push_text_to_user(
        user_id=os.getenv("All_doctor_group_id"),
        text=f"📣【重要會議提醒】\n明天({tomorrow_str})有重要院務會議，請大家準時出席唷！"
    )
