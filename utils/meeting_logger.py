# utils/meeting_logger.py

import gspread
import json
import os
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# 建立認證
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
google_creds = json.loads(os.environ['GOOGLE_CREDENTIALS'])
creds = ServiceAccountCredentials.from_json_keyfile_dict(google_creds, scope)
gc = gspread.authorize(creds)

def log_meeting_reply(user_id, name, dept, reply, reason):
    # 📝 表單網址請從外部傳入（或改寫這行）
    SHEET_URL = "https://docs.google.com/spreadsheets/d/你的ID/edit"
    sheet = gc.open_by_url(SHEET_URL).sheet1

    now = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
    sheet.append_row([now, user_id, name, dept, reply, reason])
