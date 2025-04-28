from utils.google_sheets import log_meeting_reply, get_doctor_name
from utils.state_manager import set_state, get_state, clear_state
from utils.line_push import push_text_to_user
import os

DOCTOR_SHEET_URL = "https://docs.google.com/spreadsheets/d/1fHf5XlbvLMd6ytAh_t8Bsi5ghToiQHZy1NlVfEG7VIo/edit"
RECORD_SHEET_URL = "https://docs.google.com/spreadsheets/d/1rtoP3e7D4FPzXDqv0yIOqYE9gwsdmFQSccODkbTZVDs/edit"

def handle_meeting_leave_response(user_id, user_msg):
    if get_state(user_id) == "ASK_MEETING_LEAVE":
        if user_msg.upper() == "Y":
            doctor_name = get_doctor_name(DOCTOR_SHEET_URL, user_id)
            log_meeting_reply(RECORD_SHEET_URL, user_id, doctor_name, "出席")
            clear_state(user_id)
            return "✅ 已記錄您將出席本週院務會議"
        elif user_msg.upper() == "N":
            set_state(user_id, "ASK_MEETING_REASON")
            return "請問您無法出席的原因是？"
        else:
            return "⚠️ 請輸入 Y 或 N"
    elif get_state(user_id) == "ASK_MEETING_REASON":
        doctor_name = get_doctor_name(DOCTOR_SHEET_URL, user_id)
        log_meeting_reply(RECORD_SHEET_URL, user_id, doctor_name, "請假", user_msg)
        clear_state(user_id)
        return f"✅ 已記錄您的請假原因：{user_msg}"
    return None
