# handlers/overtime_handler.py
from linebot.models import TextSendMessage, FlexSendMessage
from utils.session_manager import get_session, set_session, clear_session
import requests
import os
import pytz
from datetime import datetime

# ✅ GAS Webhook URL
GAS_WEBHOOK_URL = os.getenv("OVERTIME_GAS_URL")

def handle_overtime(event, user_id, text, line_bot_api):
    session = get_session(user_id) or {}

    if text == "加班申請":
        set_session(user_id, {"step": 1, "type": "加班申請"})
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請輸入加班日期（格式：YYYY-MM-DD）"))
        return True

    if session.get("type") != "加班申請":
        return False

    if session.get("step") == 1:
        session["date"] = text
        session["step"] = 2
        set_session(user_id, session)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請輸入加班時間（格式：HH:MM-HH:MM）"))
        return True

    if session.get("step") == 2:
        session["time"] = text
        session["step"] = 3
        set_session(user_id, session)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請輸入加班事由（需詳述，例如手術內容、病歷完成情況等）"))
        return True

    if session.get("step") == 3:
        session["reason"] = text
        session["step"] = 4
        set_session(user_id, session)

        date = session["date"]
        time_range = session["time"]
        reason = session["reason"]
        roc_date = f"{int(date[:4]) - 1911}年{date[5:7]}月{date[8:]}日"

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
                    {
                        "type": "button",
                        "style": "primary",
                        "color": "#00C300",
                        "action": {"type": "postback", "label": "✅ 確認送出", "data": "confirm_overtime"}
                    },
                    {
                        "type": "button",
                        "style": "primary",
                        "color": "#FF0000",
                        "action": {"type": "postback", "label": "❌ 取消", "data": "cancel_overtime"}
                    }
                ]
            }
        }

        line_bot_api.reply_message(event.reply_token, FlexSendMessage(alt_text="請確認加班申請", contents=flex_content))
        return True

    return False


def submit_overtime(user_id, line_bot_api, reply_token):
    import gspread
    from google.oauth2 import service_account
    import json

    session = get_session(user_id)
    if not session:
        line_bot_api.reply_message(reply_token, TextSendMessage(text="⚠️ 沒有找到加班資料，請重新輸入"))
        return

    date = session["date"]
    time_range = session["time"]
    reason = session["reason"]

    doctor_name = "未知"
    dept = "未知"
    id_number = "未填"

    try:
        creds_dict = json.loads(os.getenv("GOOGLE_CREDENTIALS"))
        creds = service_account.Credentials.from_service_account_info(creds_dict)
        client = gspread.authorize(creds)

        # ✅ 正確連接分頁名稱「UserMapping」
        sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/1fHf5XlbvLMd6ytAh_t8Bsi5ghToiQHZy1NlVfEG7VIo/edit").worksheet("UserMapping")
        rows = sheet.get_all_values()

        for row in rows[1:]:
            if len(row) >= 4 and row[0].strip() == user_id.strip():
                doctor_name = row[1].strip()
                dept = row[2].strip()
                id_number = row[3].strip()
                break

        if doctor_name == "未知":
            line_bot_api.push_message(user_id, TextSendMessage(text="⚠️ 查無您的姓名與科別，請確認是否完成帳號綁定"))

    except Exception as e:
        print(f"❌ Google Sheets 錯誤：{e}")

    tz = pytz.timezone('Asia/Taipei')
    timestamp = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")

    try:
        payload = {
            "timestamp": timestamp,
            "dept": dept,
            "name": doctor_name,
            "id_number": id_number,
            "date": date,
            "time": time_range,
            "reason": reason
        }
        print("📤 傳送加班申請：", payload)

        response = requests.post(GAS_WEBHOOK_URL, json=payload)

        if response.status_code == 200:
            line_bot_api.reply_message(reply_token, TextSendMessage(text="✅ 加班申請已送出"))
        else:
            line_bot_api.reply_message(reply_token, TextSendMessage(text=f"❌ 送出失敗：{response.text}"))

    except Exception as e:
        line_bot_api.reply_message(reply_token, TextSendMessage(text=f"❌ 發送時發生錯誤：{e}"))

    clear_session(user_id)
