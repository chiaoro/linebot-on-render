# utils/meeting_leave.py

import os, json
from dotenv import load_dotenv
from utils.google_sheets import log_meeting_reply, get_doctor_name
from utils.state_manager import set_state, get_state, clear_state
from linebot.models import TextSendMessage

load_dotenv()

# ✅ 重要表單網址
DOCTOR_SHEET_URL = "https://docs.google.com/spreadsheets/d/1fHf5XlbvLMd6ytAh_t8Bsi5ghToiQHZy1NlVfEG7VIo/edit"
RECORD_SHEET_URL = "https://docs.google.com/spreadsheets/d/1-mI71sC7TE-f8Gb9YPddhVGJrozKxLIdJlSBf2khJsA/edit"

def handle_meeting_leave_response(user_id, user_msg):
    """處理院務會議請假流程，回傳給 LINE Bot 要發送的訊息"""

    user_state = get_state(user_id)

    if user_state == "ASK_LEAVE":
        if user_msg.strip().upper() == "Y":
            doctor_name = get_doctor_name(DOCTOR_SHEET_URL, user_id) or "未知醫師"
            log_meeting_reply(RECORD_SHEET_URL, user_id, doctor_name, "出席")
            clear_state(user_id)
            return TextSendMessage(text="✅ 您已回覆出席，請當天準時與會。")
        
        elif user_msg.strip().upper() == "N":
            set_state(user_id, "ASK_REASON")
            return TextSendMessage(text="請輸入您無法出席的原因：")

        else:
            return TextSendMessage(text="⚠️ 請輸入 Y（出席）或 N（請假）以繼續。")

    elif user_state == "ASK_REASON":
        doctor_name = get_doctor_name(DOCTOR_SHEET_URL, user_id) or "未知醫師"
        log_meeting_reply(RECORD_SHEET_URL, user_id, doctor_name, "請假", reason=user_msg)
        clear_state(user_id)
        return TextSendMessage(text=f"✅ 已記錄您的請假原因：{user_msg}")

    else:
        # 如果沒有在任何流程狀態
        return TextSendMessage(text="⚠️ 請從主選單重新開始填寫會議出席情況。")
