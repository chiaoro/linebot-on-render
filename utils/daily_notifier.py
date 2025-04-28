# utils/daily_notifier.py

import os, json, gspread
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv
from utils.line_push import push_text_to_user

load_dotenv()

# Google Sheets 認證
SCOPE = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds_dict = json.loads(os.getenv("GOOGLE_CREDENTIALS"))
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
gc = gspread.authorize(creds)

# 每日推播
def run_daily_push():
    sheet = gc.open_by_url("https://docs.google.com/spreadsheets/d/1FspUjkRckA1g4bYESb7QEUKl1FzOcL5BejhOqkMD0Po/edit")
    worksheet = sheet.worksheet("每日推播")
    data = worksheet.get_all_records()

    today = datetime.now().strftime("%Y/%m/%d")
    for row in data:
        if row.get("日期") == today:
            user_id = row.get("UserID")
            message = row.get("訊息")
            if user_id and message:
                push_text_to_user(user_id, message)
