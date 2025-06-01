# handlers/adjust_handler.py

import re
import requests
from linebot.models import TextSendMessage, FlexSendMessage
from utils.session_manager import get_session, set_session, clear_session
from utils.line_utils import is_trigger
from utils.adjust_bubble import get_adjustment_bubble
from utils.doctor_info import get_doctor_name  # 自動對應醫師姓名

TRIGGER_WORDS = ["我要調診", "我要休診", "我要代診", "我要加診"]
VALID_DATE_PATTERN = r"^\d{1,2}/\d{1,2}\s*(上午診|下午診|夜診)?$"
WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbwgmpLgjrhwquI54fpK-dIA0z0TxHLEfO2KmaX-meqE7ENNUHmB_ec9GC-7MNHNl1eJ/exec"
DOCTOR_SHEET_URL = "https://docs.google.com/spreadsheets/d/1fHf5XlbvLMd6ytAh_t8Bsi5ghToiQHZy1NlVfEG7VIo/edit#gid=1930321534"

def handle_adjustment(event, user_id, text, line_bot_api):
    # ✅ 啟動流程
    if is_trigger(event, TRIGGER_WORDS):
        set_session(user_id, {
            "step": 0,
            "type": text
        })
        line_bot_api.push_message(user_id, TextSendMessage(
            text="📅 請問原本門診是哪一天？（例如：5/6 上午診）"
        ))
        return True

    session = get_session(user_id)
    step = session.get("step", -1)

    if step == 0:
        if re.match(VALID_DATE_PATTERN, text):
            session["original_date"] = text
            session["step"] = 1
            line_bot_api.push_message(user_id, TextSendMessage(
                text="📆 請問希望的新門診是哪一天？（例如：5/30 下午診）"
            ))
            line_bot_api.push_message(user_id, TextSendMessage(
                text="🔁 若為休診，請直接輸入「休診」；若為他人代診，請寫「5/30 下午診 XXX代診」"
            ))
        else:
            line_bot_api.push_message(user_id, TextSendMessage(
                text="⚠️ 格式錯誤，請輸入例如：5/6 上午診"
            ))
        set_session(user_id, session)
        return True

    elif step == 1:
        session["new_date"] = text
        session["step"] = 2
        line_bot_api.push_message(user_id, TextSendMessage(
            text="📝 請輸入原因（例如：返台、會議）"
        ))
        set_session(user_id, session)
        return True

    elif step == 2:
        session["reason"] = text
        doctor_name = get_doctor_name(DOCTOR_SHEET_URL, user_id)

        payload = {
            "user_id": user_id,
            "request_type": session["type"],
            "original_date": session["original_date"],
            "new_date": session["new_date"],
            "reason": session["reason"],
            "doctor_name": doctor_name
        }

        try:
            response = requests.post(WEBHOOK_URL, json=payload, headers={"Content-Type": "application/json"})
            print(f"📡 webhook 回傳：{response.status_code}")

            bubble = get_adjustment_bubble(
                original=session["original_date"],
                method=session["new_date"],
                reason=session["reason"]
            )
            line_bot_api.push_message(user_id, FlexSendMessage(
                alt_text="門診調整通知", contents=bubble
            ))

        except Exception as e:
            print(f"❌ webhook 發送錯誤：{e}")
            line_bot_api.push_message(user_id, TextSendMessage(
                text="⚠️ 提交失敗，請稍後再試或聯絡巧柔"
            ))

        clear_session(user_id)
        return True

    return False
