# utils/google_sheets.py

from utils.google_auth import get_gspread_client
from utils.gspread_client import get_gspread_client
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
    try:
        sheet = gc.open_by_url(MEETING_SHEET_URL).worksheet("院務會議請假")
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        doctor_name = get_doctor_name(DOCTOR_SHEET_URL, user_id)  # ✅ 自動抓姓名

        # 寫入：時間、使用者ID、醫師姓名、出席/請假、原因
        sheet.append_row([now, user_id, doctor_name, status, reason])

    except Exception as e:
        print(f"❌ log_meeting_reply 發生錯誤：{e}")

def get_doctor_info(sheet_url, user_id):
    sheet = gc.open_by_url(sheet_url).worksheet("UserMapping")  # 用共用 gspread client

    data = sheet.get_all_records()
    for row in data:
        # ⚠️ 注意：這裡的 key 名稱要和試算表一致，根據你前面的程式 get_doctor_name 用的是 "userId"
        if row.get("LINE_USER_ID") == user_id:
            return row.get("醫師姓名"), row.get("科別")  # 假設欄位叫 name 和 dept（請根據實際表格確認）

    return "未知", "未知"
