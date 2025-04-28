# ✅ night_shift_fee.py
# ✅ 處理夜點費申請 & 每日催繳提醒

import os, json, gspread
from dotenv import load_dotenv
from oauth2client.service_account import ServiceAccountCredentials
from linebot.models import TextSendMessage
from datetime import datetime

load_dotenv()

# ✅ Google Sheets 認證
SCOPE = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds_dict = json.loads(os.environ.get("GOOGLE_CREDENTIALS"))
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
gc = gspread.authorize(creds)

# ✅ LINE Bot API 初始化
from linebot import LineBotApi
line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))

# ✅ 你的 Google Sheets 試算表網址
sheet_url = "https://docs.google.com/spreadsheets/d/1rtoP3e7D4FPzXDqv0yIOqYE9gwsdmFQSccODkbTZVDs"
worksheet_name = "夜點費申請紀錄"
sheet = gc.open_by_url(sheet_url).worksheet(worksheet_name)

# ✅ 使用者對照表
doctor_sheet_url = "https://docs.google.com/spreadsheets/d/1fHf5XlbvLMd6ytAh_t8Bsi5ghToiQHZy1NlVfEG7VIo/edit"
doctor_mapping = gc.open_by_url(doctor_sheet_url).worksheet("UserMapping")

def get_doctor_name_by_user_id(user_id):
    records = doctor_mapping.get_all_records()
    for record in records:
        if str(record.get("使用者ID")) == str(user_id):
            return record.get("醫師姓名"), record.get("科別")
    return None, None

# ✅ 接收夜點費申請訊息

def handle_night_shift_request(user_id, user_msg):
    if user_msg.strip() != "夜點費申請":
        return None

    doctor_name, department = get_doctor_name_by_user_id(user_id)
    if not doctor_name:
        return "⚠️ 查無您的醫師資料，請聯絡管理員。"

    now = datetime.now()
    year = now.year
    month = now.month - 1 if now.month != 1 else 12
    if month == 12:
        year -= 1

    sheet.append_row([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), doctor_name, department, str(year), str(month), "申請中"])

    return f"✅ {doctor_name} 醫師，已登記 {year} 年 {month} 月的夜點費申請。謝謝您！"

# ✅ 每天自動催繳夜點費

def daily_night_fee_reminder():
    # ✅ 固定群組 ID (環境變數)
    group_id = os.getenv("All_doctor_group_id")

    records = sheet.get_all_records()
    doctor_done = set()

    for record in records:
        doctor_name = record.get("醫師姓名")
        year = record.get("年份")
        month = record.get("月份")
        status = record.get("狀態")

        now = datetime.now()
        target_year = now.year
        target_month = now.month - 1 if now.month != 1 else 12
        if target_month == 12:
            target_year -= 1

        if str(year) == str(target_year) and str(month) == str(target_month):
            doctor_done.add(doctor_name)

    all_doctors = [row[0] for row in doctor_mapping.get_all_values()[1:]]
    pending_doctors = [name for name in all_doctors if name and name not in doctor_done]

    if pending_doctors:
        msg = "📢 夜點費催繳提醒：\n還沒申請的醫師：\n" + "\n".join(pending_doctors)
        line_bot_api.push_message(group_id, TextSendMessage(text=msg))
    else:
        line_bot_api.push_message(group_id, TextSendMessage(text="✅ 本月夜點費申請皆已完成！"))
