# utils/meeting_leave.py

import os
from dotenv import load_dotenv
from utils.google_sheets import (
    log_meeting_reply,
    get_doctor_info
)
from utils.state_manager_google import (
    set_state,
    get_state,
    clear_state
)
from linebot.models import TextSendMessage

load_dotenv()

# ✅ 表單網址（建議集中放在 .env 也可以）
DOCTOR_SHEET_URL = "https://docs.google.com/spreadsheets/d/1fHf5XlbvLMd6ytAh_t8Bsi5ghToiQHZy1NlVfEG7VIo/edit"
RECORD_SHEET_URL = "https://docs.google.com/spreadsheets/d/1-mI71sC7TE-f8Gb9YPddhVGJrozKxLIdJlSBf2khJsA/edit"

def handle_meeting_leave_response(user_id, user_msg):
    """
    根據 user_id 和訊息內容（Y/N 或請假原因），處理院務會議請假回應，
    並記錄到 Google Sheets，最後回傳給 LINE Bot 的回覆訊息。
    """

    try:
        user_state = get_state(user_id)
        print(f"[DEBUG] 處理請假流程：user_id={user_id}, state={user_state}, msg={user_msg}")

        # ➤ 若目前狀態是詢問出席與否
        if user_state == "ASK_LEAVE":
            response = user_msg.strip().upper()

            if response == "Y":
                doctor_name, dept = get_doctor_info(DOCTOR_SHEET_URL, user_id)
                log_meeting_reply(user_id, doctor_name, dept, "出席", "")
                clear_state(user_id)
                return TextSendMessage(text="✅ 您已回覆出席，請當天準時與會。")

            elif response == "N":
                set_state(user_id, "ASK_REASON")
                return TextSendMessage(text="請輸入您無法出席的原因：")

            else:
                return TextSendMessage(text="⚠️ 請輸入 Y（出席）或 N（請假）以繼續。")

        # ➤ 若目前狀態是等待請假原因
        elif user_state == "ASK_REASON":
            doctor_name, dept = get_doctor_info(DOCTOR_SHEET_URL, user_id)
            log_meeting_reply(user_id, doctor_name, dept, "請假", reason=user_msg)
            clear_state(user_id)
            return TextSendMessage(text=f"✅ 已記錄您的請假原因：{user_msg}")

        else:
            return TextSendMessage(text="⚠️ 請從主選單重新開始填寫會議出席情況。")

    except Exception as e:
        print(f"❌ handle_meeting_leave_response 發生錯誤：{e}")
        return TextSendMessage(text="⚠️ 系統發生錯誤，請稍後再試或聯絡秘書")
