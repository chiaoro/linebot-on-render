#utils/google_sheets.py

from utils.gspread_client import get_gspread_client
from datetime import datetime

# ✅ 醫師對照表（含 LINE ID 對應、姓名、科別）
DOCTOR_SHEET_URL = "https://docs.google.com/spreadsheets/d/1fHf5XlbvLMd6ytAh_t8Bsi5ghToiQHZy1NlVfEG7VIo/edit"

# ✅ 院務會議請假紀錄表
MEETING_SHEET_URL = "https://docs.google.com/spreadsheets/d/1-mI71sC7TE-f8Gb9YPddhVGJrozKxLIdJlSBf2khJsA/edit"

# ✅ 根據 userId 取得醫師姓名（適用於舊欄位命名為 userId）
def get_doctor_name(sheet_url, user_id):
    try:
        gc = get_gspread_client()
        sheet = gc.open_by_url(sheet_url).worksheet("UserMapping")
        rows = sheet.get_all_records()
        for row in rows:
            if row.get("userId") == user_id:
                return row.get("name", "未知")
        return "未知"
    except Exception as e:
        print(f"❌ get_doctor_name 發生錯誤：{e}")
        return "未知"

# ✅ 根據 LINE_USER_ID 取得醫師姓名與科別（推薦使用）
def get_doctor_info(sheet_url, user_id):
    try:
        gc = get_gspread_client()
        sheet = gc.open_by_url(sheet_url).worksheet("UserMapping")
        rows = sheet.get_all_records()
        for row in rows:
            keys = row.keys()
            if "LINE_USER_ID" in keys and row.get("LINE_USER_ID") == user_id:
                return row.get("醫師姓名", "未知"), row.get("科別", "未知")
            elif "userId" in keys and row.get("userId") == user_id:
                return row.get("name", "未知"), row.get("dept", "未知")
        return "未知", "未知"
    except Exception as e:
        print(f"❌ get_doctor_info 發生錯誤：{e}")
        return "未知", "未知"

# ✅ 寫入請假紀錄（含科別）
def log_meeting_reply(user_id, doctor_name, dept, status, reason):
    try:
        gc = get_gspread_client()
        sheet = gc.open_by_url(MEETING_SHEET_URL).worksheet("院務會議請假")
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sheet.append_row([now, user_id, doctor_name, dept, status, reason])
        print(f"📌 已記錄：{doctor_name} ({dept}) - {status} - {reason}")
    except Exception as e:
        print(f"❌ log_meeting_reply 發生錯誤：{e}")

# ✅ 測試用寫入
def log_something():
    try:
        gc = get_gspread_client()
        sheet = gc.open_by_url(MEETING_SHEET_URL).worksheet("紀錄表")  # 確保有此分頁
        sheet.append_row(["hello", "world"])
        print("✅ log_something 成功寫入紀錄表")
    except Exception as e:
        print(f"❌ log_something 發生錯誤：{e}")
