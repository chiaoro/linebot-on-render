import os, json
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ✅ Google Sheets 認證
SCOPE = [
    'https://spreadsheets.google.com/feeds',
    'https://www.googleapis.com/auth/drive'
]
creds_dict = json.loads(os.environ.get("GOOGLE_CREDENTIALS"))
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
gc = gspread.authorize(creds)


# ✅ 試算表網址與使用者對照表分頁名稱
SHEET_URL = "https://docs.google.com/spreadsheets/d/1rtoP3e7D4FPzXDqv0yIOqYE9gwsdmFQSccODkbTZVDs/edit"
MAPPING_SHEET_URL = "https://docs.google.com/spreadsheets/d/1fHf5XlbvLMd6ytAh_t8Bsi5ghToiQHZy1NlVfEG7VIo/edit"
MAPPING_SHEET_NAME = "UserMapping"

# ✅ 固定欄位
COLUMNS = ["時間戳記", "LINE 使用者 ID", "醫師姓名", "科別", "值班日期", "班數", "處理狀態"]

# ✅ 取得醫師姓名與科別

def get_doctor_info(user_id):
    sheet = gc.open_by_url(MAPPING_SHEET_URL).worksheet(MAPPING_SHEET_NAME)
    data = sheet.get_all_records()
    for row in data:
        if row.get("LINE 使用者 ID") == user_id:
            return row.get("醫師姓名"), row.get("科別")
    return None, None

# ✅ 寫入資料到對應科別分頁

def write_to_sheet(user_id, dates):
    doctor_name, dept = get_doctor_info(user_id)
    if not doctor_name or not dept:
        return False, "查無醫師對應資料"

    cleaned_dates = [d.strip() for d in dates if d.strip()]
    date_text = ", ".join(cleaned_dates)
    count = len(cleaned_dates)
    timestamp = datetime.now().strftime("%Y/%m/%d %H:%M:%S")

    try:
        book = gc.open_by_url(SHEET_URL)
        try:
            sheet = book.worksheet(dept)
        except gspread.exceptions.WorksheetNotFound:
            sheet = book.add_worksheet(title=dept, rows="100", cols="10")
            sheet.append_row(COLUMNS)

        sheet.append_row([
            timestamp,
            user_id,
            doctor_name,
            dept,
            date_text,
            count,
            "未處理"
        ])
        return True, f"✅ 已收到 {date_text} 的申請，共 {count} 班。"
    except Exception as e:
        return False, f"❌ 發生錯誤：{e}"

# ✅ LINE webhook 使用的流程函式
user_sessions = {}  # 你可在主程式中改為共用 session 變數

def handle_night_shift_request(user_id, user_msg):
    if user_msg == "夜點費申請":
        user_sessions[user_id] = {"step": 0}
        return "📝 請問您的夜點費申報日期是？（可填多筆，用逗號分隔，例如：4/20, 4/23）"

    if user_id in user_sessions:
        step = user_sessions[user_id]["step"]
        if step == 0:
            dates = user_msg.replace("，", ",").replace(" ", "").split(",")
            success, message = write_to_sheet(user_id, dates)
            del user_sessions[user_id]  # 清除 session
            return message

    return None
