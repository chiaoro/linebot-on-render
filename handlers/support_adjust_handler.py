# handlers/support_adjust_handler.py
import requests
from linebot.models import TextSendMessage, FlexSendMessage
from utils.session_manager import get_session, set_session, clear_session
from utils.support_bubble import get_support_adjustment_bubble
from utils.command_texts import MENU_COMMANDS

WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbwLGVRboA0UDU_HluzYURY6Rw4Y8PKMfbclmbWdqpx7MAs37o18dqPkAssU1AuZrC8hxQ/exec"

def handle_support_adjustment(event, user_id, text, line_bot_api):
    session = get_session(user_id) or {}

    # Let new menu commands switch away from a stale support-adjustment flow.
    if session.get("type") == "支援醫師調診單" and text in MENU_COMMANDS:
        clear_session(user_id)
        session = {}

    # ✅ 啟動流程
    if text == "支援醫師調診單":
        set_session(user_id, {"step": 0, "type": "支援醫師調診單"})
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="👨‍⚕️ 請輸入需異動門診醫師姓名"))
        return True

    # ✅ 如果不是本流程，直接跳過
    if session.get("type") != "支援醫師調診單":
        return False

    step = session.get("step", 0)

    if step == 0:
        session["doctor_name"] = text
        session["step"] = 1
        set_session(user_id, session)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="📅 請輸入原門診日期（例如：5/6 上午診）"))
        return True

    elif step == 1:
        session["original_date"] = text
        session["step"] = 2
        set_session(user_id, session)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="⚙️ 請輸入新門診安排（例如：休診 或 調整至5/16 上午診）"))
        return True

    elif step == 2:
        session["new_date"] = text
        session["step"] = 3
        set_session(user_id, session)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="📝 請輸入原因（例如：需返台、會議）"))
        return True

    elif step == 3:
        session["reason"] = text
        send_to_webhook(session, user_id, line_bot_api)
        clear_session(user_id)
        return True

    return False

def send_to_webhook(session, user_id, line_bot_api):
    payload = {
        "user_id": user_id,
        "request_type": "支援醫師調診單",
        "doctor_name": session.get("doctor_name"),
        "original_date": session.get("original_date"),
        "new_date": session.get("new_date"),
        "reason": session.get("reason")
    }
    try:
        requests.post(WEBHOOK_URL, json=payload, timeout=10)
        bubble = get_support_adjustment_bubble(
            doctor_name=session["doctor_name"],
            original=session["original_date"],
            method=session["new_date"],
            reason=session["reason"]
        )
        line_bot_api.push_message(user_id, FlexSendMessage(alt_text="✅ 支援醫師調診單已送出", contents=bubble))
    except Exception as e:
        line_bot_api.push_message(user_id, TextSendMessage(text=f"⚠️ 提交失敗，請稍後再試\n錯誤：{e}"))
