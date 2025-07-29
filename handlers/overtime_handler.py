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

    # ✅ 啟動加班申請
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
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請輸入加班事由（需詳述）"))
        return True

    if session.get("step") == 3:
        date = session["date"]
        time_range = session["time"]
        reason = text

        session.update({"reason": reason, "step": 4})
        set_session(user_id, session)

        roc_year = int(date.split("-")[0]) - 1911
        roc_date = f"{roc_year}年{date.split('-')[1]}月{date.split('-')[2]}日"

        flex_content = {
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {"type": "text", "text": "📝 請確認加班申請", "weight": "bold", "size": "lg"},
                    {"type": "separator", "margin": "md"},
                    {"type": "text", "text": f"日期：{roc_date}"},
                    {"type": "text", "text": f"時間：{time_range}"},
                    {"type": "text", "text": f"事由：{reason}"}
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
    import gspread
    from google.oauth2 import service_account
    import json

    session = get_session(user_id)
    if not session:
        line_bot_api.reply_message(reply_token, TextSendMessage(text="⚠️ 沒有找到加班資料，請重新輸入"))
        return

    date = session.get("date")
    time_range = session.get("time")
    reason = session.get("reason")

    doctor_name = "未知"
    dept = "未知"
    id_number = "未填"

    try:
        creds_dict = json.loads(os.getenv("GOOGLE_CREDENTIALS"))
        creds = service_account.Credentials.from_service_account_info(creds_dict)
        client = gspread.authorize(creds)

        sheet = client.open_by_url(
            "https://docs.google.com/spreadsheets/d/1fHf5XlbvLMd6ytAh_t8Bsi5ghToiQHZy1NlVfEG7VIo/edit"
        ).worksheet("UserMapping")

        rows = sheet.get_all_values()
        print(f"📄 共讀取 {len(rows)-1} 筆資料，準備比對 user_id={user_id}")

        user_id_clean = user_id.strip()

        # ✅ 先輸出前 5 筆供 Debug
        print(f"✅ 前 5 筆資料：{rows[0:6]}")

        for idx, row in enumerate(rows[1:], start=2):
            line_id = row[0].strip().replace("\u200b", "")  # 移除隱藏字元
            if len(row) >= 4:
                print(f"🔍 [{idx}] 比對 → {line_id}")
            if len(row) >= 4 and line_id == user_id_clean:
                doctor_name = row[1].strip() or "未知"
                dept = row[2].strip() or "未知"
                id_number = row[3].strip() or "未填"
                print(f"✅ 找到對應：{doctor_name}, {dept}, {id_number}")
                break

        if doctor_name == "未知":
            print(f"⚠️ 沒找到 user_id 對應資料 → {user_id}")
            line_bot_api.push_message(user_id, TextSendMessage(text="⚠️ 系統未找到您的綁定資料，請確認帳號是否已綁定。"))

    except Exception as e:
        print(f"❌ Google Sheet 讀取失敗：{e}")

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
        print(f"📤 發送資料給 GAS：{payload}")

        response = requests.post(GAS_WEBHOOK_URL, json=payload)

        if response.status_code == 200:
            line_bot_api.reply_message(reply_token, TextSendMessage(text="✅ 加班申請已送出"))
        else:
            line_bot_api.reply_message(reply_token, TextSendMessage(text=f"❌ 送出失敗：{response.text}"))

    except Exception as e:
        print(f"❌ 發送 GAS 錯誤：{e}")
        line_bot_api.reply_message(reply_token, TextSendMessage(text=f"❌ 發生錯誤：{e}"))

    clear_session(user_id)
