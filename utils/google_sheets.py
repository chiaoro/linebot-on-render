
import json
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials

def get_gspread_client():
    credentials_json = os.getenv("GOOGLE_CREDENTIALS")
    if not credentials_json:
        raise ValueError("Missing GOOGLE_CREDENTIALS env var")
    credentials_dict = json.loads(credentials_json)
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    credentials = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)
    return gspread.authorize(credentials)

def log_meeting_reply(sheet_url, user_id, doctor_name, reply, reason=""):
    gc = get_gspread_client()
    sheet = gc.open_by_url(sheet_url).sheet1
    from datetime import datetime
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sheet.append_row([now, user_id, doctor_name, reply, reason])

def get_doctor_name(sheet_url, user_id):
    gc = get_gspread_client()
    sheet = gc.open_by_url(sheet_url).sheet1
    records = sheet.get_all_records()
    for row in records:
        if str(row.get("userId")).strip() == str(user_id).strip():
            return row.get("醫師姓名", "未知醫師")
    return "未知醫師"
