# handlers/support_adjust_handler.py
import requests
import logging
from linebot.models import TextSendMessage, FlexSendMessage
from utils.session_manager import get_session, set_session, clear_session
from utils.support_bubble import get_support_adjustment_bubble
from utils.command_texts import MENU_COMMANDS

WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbwLGVRboA0UDU_HluzYURY6Rw4Y8PKMfbclmbWdqpx7MAs37o18dqPkAssU1AuZrC8hxQ/exec"
logger = logging.getLogger(__name__)

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
        if not text.strip():
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="⚠️ 請輸入支援醫師姓名"))
            return True
        session["doctor_name"] = text.strip()
        session["step"] = 1
        set_session(user_id, session)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="🏥 請輸入這位支援醫師的科別（例如：婦產科）"))
        return True

    elif step == 1:
        if not text.strip():
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="⚠️ 請輸入支援醫師科別"))
            return True
        session["department"] = text.strip()
        session["step"] = 2
        set_session(user_id, session)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="📅 請輸入原門診日期（例如：5/6 上午診）"))
        return True

    elif step == 2:
        session["original_date"] = text
        session["step"] = 3
        set_session(user_id, session)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="⚙️ 請輸入新門診安排（例如：休診 或 調整至5/16 上午診）"))
        return True

    elif step == 3:
        session["new_date"] = text
        session["step"] = 4
        set_session(user_id, session)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="📝 請輸入原因（例如：需返台、會議）"))
        return True

    elif step == 4:
        session["reason"] = text
        send_to_webhook(session, user_id, line_bot_api, event.reply_token)
        clear_session(user_id)
        return True

    return False

def send_to_webhook(session, user_id, line_bot_api, reply_token):
    payload = {
        "user_id": user_id,
        "request_type": "支援醫師調診單",
        "doctor_name": session.get("doctor_name"),
        "department": session.get("department"),
        "original_date": session.get("original_date"),
        "new_date": session.get("new_date"),
        "reason": session.get("reason")
    }
    try:
        response = requests.post(WEBHOOK_URL, json=payload, timeout=(5, 15))
        response.raise_for_status()
        # Apps Script may return HTTP 200 with an application-level failure.
        try:
            result = response.json()
        except ValueError:
            result = None
        if isinstance(result, dict) and (result.get("success") is False or result.get("status") == "error"):
            raise ValueError("Apps Script reported an error")
        bubble = get_support_adjustment_bubble(
            doctor_name=session["doctor_name"],
            department=session["department"],
            original=session["original_date"],
            method=session["new_date"],
            reason=session["reason"]
        )
        line_bot_api.reply_message(reply_token, FlexSendMessage(alt_text="✅ 支援醫師調診單已送出", contents=bubble))
    except requests.Timeout:
        logger.warning("Support adjustment webhook timed out; submission status unknown")
        line_bot_api.reply_message(reply_token, TextSendMessage(text="⚠️ 系統等待回覆逾時，申請可能已送達。請先請管理者確認紀錄，避免重複提交。"))
    except (requests.RequestException, ValueError) as exc:
        logger.warning("Support adjustment webhook failed: %s", type(exc).__name__)
        line_bot_api.reply_message(reply_token, TextSendMessage(text="⚠️ 系統未能確認提交結果，請聯絡管理者查核紀錄後再決定是否重送。"))
