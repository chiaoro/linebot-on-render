# handlers/adjust_handler.py

import re
import requests
from linebot.models import TextSendMessage, FlexSendMessage
from utils.doctor_info import get_doctor_info
from utils.adjust_bubble import get_adjustment_bubble
from utils.state_manager import get_state, set_state, clear_state

VALID_DATE_PATTERN = r"^\d{1,2}/\d{1,2}(?:\s*(上午診|下午診|夜診))?$"
TRIGGER_WORDS = ["我要調診", "我要休診", "我要代診", "我要加診"]
DOCTOR_SHEET_URL = "https://docs.google.com/spreadsheets/d/1fHf5XlbvLMd6ytAh_t8Bsi5ghToiQHZy1NlVfEG7VIo/edit"
WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbwgmpLgjrhwquI54fpK-dIA0z0TxHLEfO2KmaX-meqE7ENNUHmB_ec9GC-7MNHNl1eJ/exec"

def handle_adjustment(event, user_id, text, line_bot_api):
    raw_text = text.strip()

    # ✅ Step 0：啟動流程
    if raw_text in TRIGGER_WORDS:
        session = {
            "step": 0,
            "type": raw_text
        }
        set_state(user_id, session)
        line_bot_api.push_message(user_id, TextSendMessage(text="📅 請問原本門診是哪一天？（例如：5/6 上午診）"))
        return

    # ✅ 若在流程中
    session = get_state(user_id)
    if not session:
        return

    step = session.get("step", 0)

    # ✅ Step 1：原門診
    if step == 0:
        if re.match(VALID_DATE_PATTERN, raw_text):
            session["original_date"] = raw_text
            session["step"] = 1
            set_state(user_id, session)
            line_bot_api.push_message(user_id, TextSendMessage(text="📆 請問希望的新門診是哪一天？（或輸入「休診」、「XX代診」）"))
        else:
            line_bot_api.push_message(user_id, TextSendMessage(text="⚠️ 格式錯誤，請輸入例如：5/6 上午診"))
        return

    # ✅ Step 2：新門診處理方式
    if step == 1:
        session["new_date"] = raw_text
        session["step"] = 2
        set_state(user_id, session)
        line_bot_api.push_message(user_id, TextSendMessage(text="📝 請輸入原因（例如：返台、開會）"))
        return

    # ✅ Step 3：輸入原因並送出
    if step == 2:
        session["reason"] = raw_text

        doctor_name, dept = get_doctor_info(DOCTOR_SHEET_URL, user_id)
        if not doctor_name:
            line_bot_api.push_message(user_id, TextSendMessage(text="⚠️ 查無醫師資訊，請確認是否綁定"))
            clear_state(user_id)
            return

        payload = {
            "user_id": user_id,
            "original_date": session["original_date"],
            "new_date": session["new_date"],
            "reason": session["reason"],
            "request_type": session["type"]
        }

        try:
            response = requests.post(WEBHOOK_URL, json=payload)
            response.raise_for_status()

            bubble = get_adjustment_bubble(
                original=session["original_date"],
                method=session["new_date"],
                reason=session["reason"]
            )
            line_bot_api.push_message(user_id, FlexSendMessage(
                alt_text="門診調整已完成", contents=bubble
            ))
        except Exception as e:
            print(f"[ERROR] Webhook 發送失敗：{e}")
            line_bot_api.push_message(user_id, TextSendMessage(text="⚠️ 提交失敗，請稍後再試或聯絡巧柔"))

        clear_state(user_id)
        return

