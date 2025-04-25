import os, json
from datetime import datetime, timedelta
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ✅ LINE Bot
from linebot import LineBotApi
from linebot.models import TextSendMessage

# ✅ Google Sheets 認證
SCOPE = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds_dict = json.loads(os.environ.get("GOOGLE_CREDENTIALS"))
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
gc = gspread.authorize(creds)

# ✅ LINE Bot access token
line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))

# ✅ 設定資料表網址與分頁名稱
SHEET_URL = "https://docs.google.com/spreadsheets/d/1rtoP3e7D4FPzXDqv0yIOqYE9gwsdmFQSccODkbTZVDs/edit"
MAPPING_SHEET_URL = "https://docs.google.com/spreadsheets/d/1fHf5XlbvLMd6ytAh_t8Bsi5ghToiQHZy1NlVfEG7VIo/edit"
MAPPING_SHEET_NAME = "UserMapping"
REMINDER_SHEET_NAME = "夜點費提醒名單"

# ✅ 取得醫師姓名與科別
def get_doctor_info(user_id):
    sheet = gc.open_by_url(MAPPING_SHEET_URL).worksheet(MAPPING_SHEET_NAME)
    data = sheet.get_all_records()
    for row in data:
        normalized = {k.strip().lower(): v for k, v in row.items()}
        if str(normalized.get("line_user_id")).strip() == str(user_id).strip():
            return normalized.get("姓名"), normalized.get("科別")
    return None, None

# ✅ 由醫師姓名找 LINE ID
def get_line_id_by_name(name):
    sheet = gc.open_by_url(MAPPING_SHEET_URL).worksheet(MAPPING_SHEET_NAME)
    data = sheet.get_all_records()
    for row in data:
        if row.get("姓名") == name:
            return row.get("LINE_USER_ID")
    return None

# ✅ 展開區間格式的日期（如 4/25-29）
def expand_date_range(text):
    result = []
    for part in text.split(','):
        part = part.strip()
        if '-' in part and '/' in part:
            try:
                prefix, range_part = part.split('/')
                start, end = map(int, range_part.split('-'))
                for day in range(start, end + 1):
                    result.append(f"{prefix}/{day}")
            except:
                result.append(part)
        else:
            result.append(part)
    return result

# ✅ 寫入資料到對應科別分頁
def write_to_sheet(user_id, dates):
    doctor_name, dept = get_doctor_info(user_id)

    if not doctor_name:
        doctor_name = "未知醫師"
    if not dept:
        dept = "未分類"

    cleaned_dates = expand_date_range(dates)
    cleaned_dates = [d.strip() for d in cleaned_dates if d.strip()]
    date_text = ", ".join(cleaned_dates)
    count = len(cleaned_dates)
    timestamp = datetime.now().strftime("%Y/%m/%d %H:%M:%S")

    try:
        book = gc.open_by_url(SHEET_URL)
        try:
            sheet = book.worksheet(dept)
        except gspread.exceptions.WorksheetNotFound:
            sheet = book.add_worksheet(title=dept, rows="100", cols="10")
            sheet.append_row(["時間戳記", "LINE 使用者 ID", "醫師姓名", "科別", "值班日期", "班數", "處理狀態"])

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

# ✅ 處理 LINE Bot 夜點費申請對話
user_sessions = {}

def handle_night_shift_request(user_id, user_msg):
    if user_msg == "夜點費申請":
        user_sessions[user_id] = {"step": 0}
        return "📝 請問您的夜點費申報日期是？（可填多筆，用逗號分隔，例如：4/20, 4/23）"

    if user_id in user_sessions:
        step = user_sessions[user_id]["step"]
        if step == 0:
            success, message = write_to_sheet(user_id, user_msg)
            del user_sessions[user_id]
            return message

    return None

# ✅ 每日提醒未繳交夜點費的醫師
def daily_night_fee_reminder():
    today = datetime.today()
    last_month = today.month - 1 if today.month > 1 else 12
    last_month_str = str(last_month)

    reminder_sheet = gc.open_by_url(SHEET_URL).worksheet(REMINDER_SHEET_NAME)
    reminder_list = reminder_sheet.col_values(1)[1:]  # 取第1欄，去掉表頭

    book = gc.open_by_url(SHEET_URL)
    all_worksheets = book.worksheets()

    for name in reminder_list:
        found = False
        for sheet in all_worksheets:
            if sheet.title in ["內科", "外科", "醫療部"]:
                records = sheet.get_all_records()
                for row in records:
                    if row.get("醫師姓名") == name:
                        # 檢查這筆資料的時間戳記是不是上個月
                        try:
                            record_date = datetime.strptime(row.get("時間戳記").split(" ")[0], "%Y/%m/%d")
                            if record_date.month == last_month:
                                found = True
                                break
                        except:
                            continue
            if found:
                break

        if not found:
            # 沒有填夜點費，要傳送提醒
            line_id = get_line_id_by_name(name)
            if line_id:
                message = f"📣 [夜點費提醒通知]\n{name} 醫師您好，目前尚未收到您 {last_month} 月份的夜點費申報，請盡快填寫 🙏"
                line_bot_api.push_message(line_id, TextSendMessage(text=message))
