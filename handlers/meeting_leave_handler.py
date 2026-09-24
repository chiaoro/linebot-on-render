import logging

import requests
from linebot.models import TextSendMessage

from utils.command_texts import MENU_COMMANDS
from utils.doctor_info import DoctorDirectoryUnavailable, get_doctor_info
from utils.meeting_leave_menu import get_meeting_leave_menu, get_meeting_leave_success
from utils.state_manager import get_state, set_state, clear_state

logger = logging.getLogger(__name__)
_http = requests.Session()

# ✅ Webhook URL（請假資料送出處）
WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbyk8tqbMREdzaWpwJ5ZE0CJsC_0JmsE1QRW1-S0ALvYVYuCQxlVELCI8GrvpUjF6pPg/exec"

# ✅ 醫師對照表網址（查姓名與科別）
DOCTOR_SHEET_URL = "https://docs.google.com/spreadsheets/d/1fHf5XlbvLMd6ytAh_t8Bsi5ghToiQHZy1NlVfEG7VIo/edit"

def log_meeting_reply(user_id, doctor_name, dept, status, reason):
    payload = {
        "user_id": user_id,
        "doctor_name": doctor_name,
        "department": dept,
        "status": status,
        "reason": reason
    }

    try:
        response = _http.post(WEBHOOK_URL, json=payload, timeout=(3.05, 12))
        response.raise_for_status()
        logger.info("Meeting leave submission succeeded: status=%s", status)
    except Exception as e:
        logger.error(
            "Meeting leave submission failed: status=%s error=%s",
            status,
            type(e).__name__,
        )
        raise


def _reply_temporary_failure(event, line_bot_api, retry_instruction):
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(
            text=f"⚠️ 外部服務暫時忙碌，本次尚未完成登記。\n{retry_instruction}"
        ),
    )


def _get_bound_doctor(user_id):
    doctor_name, dept = get_doctor_info(DOCTOR_SHEET_URL, user_id)
    if not doctor_name:
        raise LookupError("查無對應醫師資訊")
    return doctor_name, dept

def handle_meeting_leave(event, user_id, text, line_bot_api):
    raw_text = event.message.text.strip()

    # ✅ 初次進入：觸發請假流程
    if raw_text == "院務會議請假":
        set_state(user_id, "ASK_LEAVE")
        line_bot_api.reply_message(event.reply_token, get_meeting_leave_menu())
        return True

    state = get_state(user_id)

    # Let new menu commands switch away from a stale meeting-leave flow.
    if state in ["ASK_LEAVE", "ASK_REASON"] and raw_text in MENU_COMMANDS:
        clear_state(user_id)
        return False

    # ✅ 使用者點選出席或請假
    if state == "ASK_LEAVE":
        if raw_text == "我要出席院務會議":
            try:
                doctor_name, dept = _get_bound_doctor(user_id)
                log_meeting_reply(user_id, doctor_name, dept, "出席", "")
            except LookupError:
                clear_state(user_id)
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="⚠️ 查無您的醫師綁定資料，請聯絡巧柔協助。"))
            except DoctorDirectoryUnavailable:
                _reply_temporary_failure(event, line_bot_api, "請直接再點一次「出席」，不需重新開啟流程。")
            except Exception:
                logger.exception("Unexpected meeting attendance submission failure")
                _reply_temporary_failure(event, line_bot_api, "請直接再點一次「出席」，不需重新開啟流程。")
            else:
                clear_state(user_id)
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="✅ 您已回覆出席，請當天準時與會。"))
        elif raw_text == "我要請假院務會議":
            set_state(user_id, "ASK_REASON")
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="📝 請輸入您無法出席的原因："))
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="⚠️ 請點選上方按鈕回覆"))
        return True

    # ✅ 請假者輸入原因
    if state == "ASK_REASON":
        reason = raw_text
        try:
            doctor_name, dept = _get_bound_doctor(user_id)
            log_meeting_reply(user_id, doctor_name, dept, "請假", reason)
        except LookupError:
            clear_state(user_id)
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="⚠️ 查無您的醫師綁定資料，請聯絡巧柔協助。"))
        except DoctorDirectoryUnavailable:
            _reply_temporary_failure(event, line_bot_api, "請直接再傳一次請假原因，不需重新開啟流程。")
        except Exception:
            logger.exception("Unexpected meeting leave submission failure")
            _reply_temporary_failure(event, line_bot_api, "請直接再傳一次請假原因，不需重新開啟流程。")
        else:
            clear_state(user_id)
            line_bot_api.reply_message(event.reply_token, get_meeting_leave_success(reason))
        return True

    return False
