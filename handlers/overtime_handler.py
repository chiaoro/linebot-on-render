# handlers/overtime_handler.py
from linebot.models import TextSendMessage, FlexSendMessage
from utils.session_manager import get_session, set_session, clear_session
import requests
import os
import pytz
from datetime import datetime
from utils.command_texts import MENU_COMMANDS

# ✅ GAS Webhook URL
GAS_WEBHOOK_URL = os.getenv("OVERTIME_GAS_URL")

def handle_overtime(event, user_id, text, line_bot_api):
    session = get_session(user_id) or {}

    # Let new menu commands switch away from a stale overtime flow.
    if session.get("type") == "加班申請" and text in MENU_COMMANDS:
        clear_session(user_id)
        session = {}

    # ✅ 啟動加班申請
    if text == "加班申請":
        set_session(user_id, {"step": 1, "type": "加班申請"})
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請輸入加班日期（格式：YYYY-MM-DD）"))
        return True

    if session.get("type") != "加班申請":
        return False

    # Step 1：輸入日期
    if session.get("step") == 1:
        session["date"] = text
        session["step"] = 2
        set_session(user_id, session)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請輸入加班時間（格式：HH:MM-HH:MM）"))
        return True

    # Step 2：輸入時間
    if session.get("step") == 2:
        session["time"] = text
        session["step"] = 3
        set_session(user_id, session)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請輸入加班事由（需詳述,例如開了什麼刀、完成哪幾份病歷、查哪幾間房等等）"))
        return True

    # Step 3：確認
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
                    {
                        "type": "button", "style": "primary", "color": "#00C300",
                        "action": {"type": "postback", "label": "✅ 確認送出", "data": "confirm_overtime"}
                    },
                    {
                        "type": "button", "style": "primary", "color": "#FF0000",
                        "action": {"type": "postback", "label": "❌ 取消", "data": "cancel_overtime"}
                    }
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

    date = session["date"]
    time_range = session["time"]
    reason = session["reason"]

    # ✅ 產生台灣時間
    tz = pytz.timezone('Asia/Taipei')
    timestamp = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")

    # ✅ 傳送給 GAS（只送 user_id + 申請資訊）
    payload = {
        "timestamp": timestamp,
        "user_id": user_id,
        "date": date,
        "time": time_range,
        "reason": reason
    }

    try:
        response = requests.post(GAS_WEBHOOK_URL, json=payload)
        if response.status_code == 200:
            line_bot_api.reply_message(reply_token, TextSendMessage(text="✅ 加班申請已送出，後臺已登記。"))
        else:
            line_bot_api.reply_message(reply_token, TextSendMessage(text=f"❌ 送出失敗：{response.text}"))
    except Exception as e:
        line_bot_api.reply_message(reply_token, TextSendMessage(text=f"❌ 發生錯誤：{e}"))

    clear_session(user_id)
