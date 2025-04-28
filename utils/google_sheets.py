# utils/google_sheets.py

from utils.google_auth import get_gspread_client

DOCTOR_SHEET_URL = "https://docs.google.com/spreadsheets/d/1fHf5XlbvLMd6ytAh_t8Bsi5ghToiQHZy1NlVfEG7VIo/edit"
RECORD_SHEET_URL = "https://docs.google.com/spreadsheets/d/1-mI71sC7TE-f8Gb9YPddhVGJrozKxLIdJlSBf2khJsA/edit"

def get_doctor_name(sheet_url, user_id):
    gc = get_gspread_client()
    sheet = gc.open_by_url(sheet_url).worksheet("UserMapping")
    rows = sheet.get_all_records()
    for row in rows:
        if row.get("userId") == user_id:
            return row.get("name")
    return "未知"

def log_meeting_reply(sheet_url, user_id, doctor_name, status, reason=None):
    gc = get_gspread_client()
    sheet = gc.open_by_url(sheet_url).worksheet("院務會議請假")
    now = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
    sheet.append_row([now, doctor_name, status, reason or ""])
