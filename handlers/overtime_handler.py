# handlers/overtime_handler.py
from linebot.models import TextSendMessage, FlexSendMessage
from utils.session_manager import get_session, set_session, clear_session
import requests
import os
import pytz
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

# ✅ GAS Webhook URL
OVERTIME_GAS_URL = os.getenv("OVERTIME_GAS_URL")
DOCTOR_SHEET_URL = "https://docs.google.com/spreadsheets/d/1fHf5XlbvLMd6ytAh_t8Bsi5ghToiQHZy1NlVfEG7VIo/edit"

# ✅ 專屬函式：抓醫師姓名 & 科別
def get_doctor_info_for_overtime(user_id):
    try:
        creds_dict = json.loads(os.getenv("GOOGLE_CREDENTIALS"))
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        gc = gspread.authorize(ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope))
        sh = gc.open_by_url(DOCTOR_SHEET_URL)
        worksheet = sh.worksheet("UserMapping")
        records = worksheet.get_all_records()

        for row in records:
            if str(row.get("LINE_USER_ID")).strip() == str(user_id).strip():
                return row.get("姓名", "未知"), row.get("科別", "未知")
        return "未知", "未知"
    except Exception as e:
        print(f"[ERROR] 讀取醫師資料失敗：{e}")
        return "未知", "未知"


def handle_overtime(event, user_id, text, line_bot_api):
    session = get_session(user_id) or {}

    if text == "加班申請":
        set_session(user_id, {"step": 1})
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請輸入加班日期（格式：YYYY-MM-DD）"))
        return True

    if session.get("step") == 1:
        set_session(user_id, {"step": 2, "date": text})
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請輸入加班時間（格式：HH:MM-HH:MM）"))
        return True

    if session.get("step") == 2:
        set_session(user_id, {"step": 3, "date": session["date"], "time": text})
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請輸入加班事由"))
        return True

    if session.get("step") == 3:
        date = session["date"]
        time_range = session["time"]
        reason = text

        # ✅ 轉換日期 → 民國格式
        roc_year = int(date.split("-")[0]) - 1911
        roc_date = f"{roc_year}年{date.split('-')[1]}月{date.split('-')[2]}日"

        # ✅ 存回 Session
        set_session(user_id, {"step": 4, "date": date, "time": time_range, "reason": reason})

        flex_content = {
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {"type": "text", "text": "📝 請確認加班申請", "weight": "bold", "size": "lg"},
                    {"type": "separator", "margin": "md"},
                    {"type": "text", "text": f"日期：{roc_date}", "margin": "sm"},
                    {"type": "text", "text": f"時間：{time_range}", "margin": "sm"},
                    {"type": "text", "text": f"事由：{reason}", "margin": "sm"}
                ]
            },
            "footer": {
                "type": "box",
                "layout": "horizontal",
                "contents": [
                    {"type": "button", "style": "primary", "color": "#00C300",
                     "action": {"type": "postback", "label": "✅ 確認送出", "data": "confirm_overtime"}},
                    {"type": "button", "style": "primary", "color": "#FF0000",
                     "action": {"type": "postback", "label": "❌ 取消", "data": "cancel_overtime"}}
                ]
            }
        }

        line_bot_api.reply_message(event.reply_token, FlexSendMessage(alt_text="請確認加班申請", contents=flex_content))
        return True

    return False


def submit_overtime(user_id, line_bot_api, reply_token):
    session = get_session(user_id)
    if not session:
        line_bot_api.reply_message(reply_token, TextSendMessage(text="⚠️ 沒有找到加班資料，請重新輸入"))
        return

    date = session.get("date")
    time_range = session.get("time")
    reason = session.get("reason")

    # ✅ 取得醫師姓名與科別（使用新函式）
    doctor_name, dept = get_doctor_info_for_overtime(user_id)

    # ✅ 台灣時間戳記
    tz = pytz.timezone('Asia/Taipei')
    timestamp = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")

    # ✅ 呼叫 GAS
    try:
        response = requests.post(OVERTIME_GAS_URL, json={
            "timestamp": timestamp,
            "dept": dept,
            "name": doctor_name,
            "date": date,
            "time": time_range,
            "reason": reason
        })
        if response.status_code == 200:
            line_bot_api.reply_message(reply_token, TextSendMessage(text="✅ 加班申請已送出並同步至後台"))
        else:
            line_bot_api.reply_message(reply_token, TextSendMessage(text=f"❌ 送出失敗：{response.text}"))
    except Exception as e:
        line_bot_api.reply_message(reply_token, TextSendMessage(text=f"❌ 發生錯誤：{e}"))

    clear_session(user_id)
