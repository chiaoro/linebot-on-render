# utils/doctor_info.py

import json
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from gspread.exceptions import WorksheetNotFound

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
google_creds = json.loads(os.environ['GOOGLE_CREDENTIALS'])
creds = ServiceAccountCredentials.from_json_keyfile_dict(google_creds, scope)
gc = gspread.authorize(creds)

def get_doctor_info(sheet_url, user_id):
    try:
        gc = gspread.service_account(filename="credentials.json")  # 或你的憑證方式
        sheet = gc.open_by_url(sheet_url).worksheet("UserMapping")
    except WorksheetNotFound:
        print("❌ 找不到工作表：UserMapping")
        return None, None

    # 例如根據 user_id 查資料的邏輯
    rows = sheet.get_all_records()
    for row in rows:
        if row.get("user_id") == user_id:
            return row.get("name"), row.get("dept")

    return None, None
