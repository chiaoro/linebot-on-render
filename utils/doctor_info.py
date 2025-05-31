# utils/doctor_info.py

import json
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
google_creds = json.loads(os.environ['GOOGLE_CREDENTIALS'])
creds = ServiceAccountCredentials.from_json_keyfile_dict(google_creds, scope)
gc = gspread.authorize(creds)

def get_doctor_info(sheet_url, user_id):
    sheet = gc.open_by_url(sheet_url).worksheet("UserMapping")
    records = sheet.get_all_records()
    for row in records:
        if row["user_id"] == user_id:
            return row["name"], row["dept"]
    return "未知", "未知"
