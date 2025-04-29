# utils/google_sheets.py

from utils.google_auth import get_gspread_client
from utils.gspread_client import gc
from datetime import datetime

# ✅ 醫師對照表 & 院務會議請假紀錄表
DOCTOR_SHEET_URL = "https://docs.google.com/spreadsheets/d/1fHf5XlbvLMd6ytAh_t8Bsi5ghToiQHZy1NlVfEG7VIo/edit"
MEETING_SHEET_URL = "https://docs.google.com/spreadsheets/d/1-mI71sC7TE-f8Gb9YPddhVGJrozKxLIdJlSBf2khJsA/edit"

def get_doctor_name(sheet_url, user_id):
    """
    根據 user_id 回傳醫師姓名
    """
    gc = get_gspread_client()
    sheet = gc.open_by_url(sheet_url).worksheet("UserMapping")
    rows = sheet.get_all_records()
    for row in rows:
        if row.get("userId") == user_id:
            return row.get("name")
    return "未知"

def log_meeting_reply(user_id, status, reason):
    """
    紀錄院務會議的出席或請假
    """
    try:
        sheet = gc.open_by_url(MEETING_SHEET_URL).worksheet("院務會議請假")
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sheet.append_row([now, user_id, status, reason])
    except Exception as e:
        print(f"❌ log_meeting_reply 發生錯誤：{e}")
