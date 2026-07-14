#utils/google_sheets.py

from utils.gspread_client import get_gspread_client
from utils.sheet_cache import get_sheet_values_by_url
from datetime import datetime

# ✅ 醫師對照表（含 LINE ID 對應、姓名、科別）
DOCTOR_SHEET_URL = "https://docs.google.com/spreadsheets/d/1fHf5XlbvLMd6ytAh_t8Bsi5ghToiQHZy1NlVfEG7VIo/edit"

# ✅ 院務會議請假紀錄表
MEETING_SHEET_URL = "https://docs.google.com/spreadsheets/d/1-mI71sC7TE-f8Gb9YPddhVGJrozKxLIdJlSBf2khJsA/edit"

# ✅ 根據 userId 取得醫師姓名（適用於舊欄位命名為 userId）
def get_doctor_name(sheet_url, user_id):
    try:
        values = get_sheet_values_by_url(sheet_url, "UserMapping")
        if not values:
            return "未知"

        headers = values[0]
        user_id_idx = headers.index("userId") if "userId" in headers else 0
        name_idx = headers.index("name") if "name" in headers else 1

        rows = values[1:]
        for row in rows:
            if len(row) > user_id_idx and row[user_id_idx] == user_id:
                return row[name_idx] if len(row) > name_idx and row[name_idx] else "未知"
        return "未知"
    except Exception as e:
        print(f"❌ get_doctor_name 發生錯誤：{e}")
        return "未知"

# ✅ 根據 LINE_USER_ID 取得醫師姓名與科別（推薦使用）
def get_doctor_info(sheet_url, user_id):
    try:
        values = get_sheet_values_by_url(sheet_url, "UserMapping")
        if not values:
            return "未知", "未知"

        headers = values[0]
        for row in values[1:]:
            row_dict = {
                header: row[idx] if idx < len(row) else ""
                for idx, header in enumerate(headers)
            }

            if row_dict.get("LINE_USER_ID") == user_id:
                return row_dict.get("醫師姓名", "未知"), row_dict.get("科別", "未知")
            elif row_dict.get("userId") == user_id:
                return row_dict.get("name", "未知"), row_dict.get("dept", "未知")
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
