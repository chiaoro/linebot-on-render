# utils/meeting_leave.py

import gspread
import os, json
from dotenv import load_dotenv
from oauth2client.service_account import ServiceAccountCredentials
from utils.google_sheets import log_meeting_reply, get_doctor_name
from utils.state_manager import set_state, get_state, clear_state

load_dotenv()

# ✅ Google Sheets 認證
SCOPE = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds_dict = json.loads(os.getenv("GOOGLE_CREDENTIALS"))
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
gc = gspread.authorize(creds)

# ✅ 重要表單網址
DOCTOR_SHEET_URL = "https://docs.google.com/spreadsheets/d/1fHf5XlbvLMd6ytAh_t8Bsi5ghToiQHZy1NlVfEG7VIo/edit"
RECORD_SHEET_URL = "https://docs.google.com/spreadsheets/d/1-mI71sC7TE-f8Gb9YPddhVGJrozKxLIdJlSBf2khJsA/edit"

def handle_meeting_leave_response(user_id, user_msg, line_bot_api, event):
    """處理院務會議請假的流程"""

    if get_state(user_id) == "ASK_LEAVE":
        if user_msg.upper() == "Y":
            doctor_name = get_doctor_name(DOCTOR_SHEET_URL, user_id)
            log_meeting_reply(RECORD_SHEET_URL, user_id, doctor_name, "出席")
            clear_state(user_id)
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="✅ 您已回覆出席，請當天準時與會。"))
        elif user_msg.upper() == "N":
            set_state(user_id, "ASK_REASON")
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請輸入您無法出席的原因："))
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請輸入 Y（出席）或 N（請假）"))

    elif get_state(user_id) == "ASK_REASON":
        doctor_name = get_doctor_name(DOCTOR_SHEET_URL, user_id)
        log_meeting_reply(RECORD_SHEET_URL, user_id, doctor_name, "請假", user_msg)
        clear_state(user_id)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"✅ 已記錄您的請假原因：{user_msg}"))

