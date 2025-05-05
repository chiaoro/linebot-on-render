#utils/google_sheets.py


from utils.gspread_client import get_gspread_client
from datetime import datetime


DOCTOR_SHEET_URL = "https://docs.google.com/spreadsheets/d/1fHf5XlbvLMd6ytAh_t8Bsi5ghToiQHZy1NlVfEG7VIo/edit"
MEETING_SHEET_URL = "https://docs.google.com/spreadsheets/d/1-mI71sC7TE-f8Gb9YPddhVGJrozKxLIdJlSBf2khJsA/edit"

def get_doctor_name(sheet_url, user_id):
    gc = get_gspread_client()
    sheet = gc.open_by_url(sheet_url).worksheet("UserMapping")
    rows = sheet.get_all_records()
    for row in rows:
        if row.get("userId") == user_id:
            return row.get("name")
    return "未知"

def log_meeting_reply(user_id, doctor_name, dept, status, reason):
    try:
        gc = get_gspread_client()
        sheet = gc.open_by_url(MEETING_SHEET_URL).worksheet("院務會議請假")
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 寫入：時間、使用者ID、醫師姓名、科別、回覆內容、請假原因
        sheet.append_row([now, user_id, doctor_name, dept, status, reason])

    except Exception as e:
        print(f"❌ log_meeting_reply 發生錯誤：{e}")

def get_doctor_info(sheet_url, user_id):
    gc = get_gspread_client()
    sheet = gc.open_by_url(sheet_url).worksheet("UserMapping")

    data = sheet.get_all_records()
    for row in data:
        if row.get("LINE_USER_ID") == user_id:
            return row.get("醫師姓名"), row.get("科別")

    return "未知", "未知"





def log_something():
    gc = get_gspread_client()
    sheet = gc.open_by_url(...).worksheet("記錄表")
    sheet.append_row(["hello", "world"])
