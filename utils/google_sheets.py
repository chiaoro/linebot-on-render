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

def log_meeting_reply(user_id, status, reason):
    """
    把院務會議出席/請假狀態紀錄到 Google Sheets
    user_id：使用者的 LINE ID
    status：'出席' 或 '請假'
    reason：如果請假，要記錄原因
    """
    try:
        # 開啟試算表
        sheet = gc.open_by_url(MEETING_SHEET_URL).worksheet("院務會議請假")
        
        # 找到現在時間
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 寫入一列資料：時間、user_id、出席/請假、原因
        sheet.append_row([now, user_id, status, reason])
        
    except Exception as e:
        print(f"❌ 紀錄院務會議請假失敗：{str(e)}")
