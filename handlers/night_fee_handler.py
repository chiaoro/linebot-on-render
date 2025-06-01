# handlers/night_fee_handler.py

from linebot.models import FlexSendMessage, TextSendMessage
from utils.session_manager import get_session, set_session, clear_session
from utils.date_parser import parse_dates_from_text
import re

def handle_night_fee(event, user_id, text, line_bot_api):
    session = get_session(user_id)
    step = session.get("step", 0)

    # ✅ 使用者輸入關鍵字「夜點費申請」
    if text == "夜點費申請":
        set_session(user_id, {"step": 1})
        line_bot_api.reply_message(event.reply_token, get_night_fee_input_flex())
        return True

    # ✅ 使用者輸入日期（可多筆）
    if step == 1 and is_valid_date_input(text):
        parsed_dates = parse_dates_from_text(text)
        date_str = "、".join(parsed_dates)
        reply = f"✅ 夜點費申請已收到\n🗓 日期：{date_str}\n我們會儘速處理，謝謝！"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
        clear_session(user_id)
        return True

    return False

# ✅ 檢查日期輸入是否為合法格式（例：5/1、5/2、5/3-5/5）
def is_valid_date_input(text):
    return all(re.match(r"^\d{1,2}/\d{1,2}$", d.strip()) or "-" in d for d in re.split(r"[、,，\s]+", text) if d.strip())

# ✅ 回傳 Flex Bubble 畫面
def get_night_fee_input_flex():
    return FlexSendMessage(
        alt_text="🌙 夜點費申請",
        contents={
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "spacing": "md",
                "contents": [
                    {"type": "text", "text": "🌙 夜點費申請", "weight": "bold", "size": "lg"},
                    {"type": "text", "text": "請輸入值班日期（可輸入區間）", "wrap": True},
                    {"type": "text", "text": "範例：\n4/10\n4/15\n4/17\n4/18-23", "size": "sm", "color": "#888", "wrap": True}
                ]
            }
        }
    )
