# handlers/meeting_leave_handler.py
from linebot.models import TextSendMessage
from utils.state_manager import get_state, set_state, clear_state
from utils.meeting_leave_menu import get_meeting_leave_menu, get_meeting_leave_success
from utils.doctor_info import get_doctor_info
from utils.meeting_logger import log_meeting_reply

DOCTOR_SHEET_URL = "https://docs.google.com/spreadsheets/d/1fHf5XlbvLMd6ytAh_t8Bsi5ghToiQHZy1NlVfEG7VIo/edit"

def handle_meeting_leave(event, user_id, text, line_bot_api):
    raw_text = event.message.text.strip()

    if raw_text == "院務會議請假":
        print(f"[DEBUG] 觸發院務會議請假，user_id={user_id}")
        set_state(user_id, "ASK_LEAVE")
        line_bot_api.reply_message(event.reply_token, get_meeting_leave_menu())
        return True

    state = get_state(user_id)

    if state == "ASK_LEAVE":
        if raw_text == "我要出席院務會議":
            doctor_name, dept = get_doctor_info(DOCTOR_SHEET_URL, user_id)
            log_meeting_reply(user_id, doctor_name, dept, "出席", "")
            clear_state(user_id)
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="✅ 您已回覆出席，請當天準時與會。"))
        elif raw_text == "我要請假院務會議":
            set_state(user_id, "ASK_REASON")
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="📝 請輸入您無法出席的原因："))
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="⚠️ 請點選上方按鈕回覆"))
        return True

    if state == "ASK_REASON":
        reason = raw_text
        doctor_name, dept = get_doctor_info(DOCTOR_SHEET_URL, user_id)
        try:
            log_meeting_reply(user_id, doctor_name, dept, "請假", reason)
            print(f"[DEBUG] 已紀錄請假：{doctor_name}（{dept}） - {reason}")
            line_bot_api.reply_message(event.reply_token, get_meeting_leave_success(reason))
        except Exception as e:
            print(f"[ERROR] 請假紀錄失敗：{e}")
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="⚠️ 系統錯誤，請稍後再試"))
        clear_state(user_id)
        return True

    return False
