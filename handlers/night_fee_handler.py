# handlers/night_fee_handler.py

from linebot.models import FlexSendMessage, TextSendMessage
from utils.session_manager import get_session, set_session, clear_session
from utils.date_parser import expand_date_range  # 你自己的展開區間函式
import requests

def handle_night_fee(event, user_id, text, line_bot_api):
    session = get_session(user_id)
    step = session.get("step", 0)

    # ✅ 觸發申請
    if text == "夜點費申請":
        set_session(user_id, {"step": 1, "type": "夜點費申請"})
        bubble = {
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {"type": "text", "text": "🌙 夜點費申請", "weight": "bold", "size": "lg"},
                    {"type": "text", "text": "請輸入值班日期（可輸入區間）", "margin": "md"},
                    {"type": "text", "text": "範例：\n4/10、4/15、4/17、4/18-23", "size": "sm", "color": "#888888", "margin": "md"}
                ]
            }
        }
        flex_msg = FlexSendMessage(alt_text="🌙 夜點費申請", contents=bubble)
        line_bot_api.reply_message(event.reply_token, flex_msg)
        return True

    # ✅ 使用者回填日期（處於夜點費流程中）
    if session.get("type") == "夜點費申請" and step == 1:
        raw_input = event.message.text.strip()
        try:
            expanded_dates = expand_date_range(raw_input)
            count = len(expanded_dates)
        except Exception as e:
            print(f"[ERROR] expand_date_range failed: {e}")
            line_bot_api.reply_message(event.reply_token, TextSendMessage(
                text="⚠️ 日期格式有誤，請重新輸入。\n範例：4/10、4/12、4/15-18"
            ))
            clear_session(user_id)
            return True

        webhook_url = "https://script.google.com/macros/s/AKfycbxOKltHGgoz05CKpTJIu4kFdzzmKd9bzL7bT5LOqYu5Lql6iaTlgFI9_lHwqFQFV8-J/exec"
        payload = {
            "user_id": user_id,
            "日期": raw_input
        }

        try:
            response = requests.post(webhook_url, json=payload)
            print("📡 webhook 回傳：", response.status_code, response.text)

            if response.status_code != 200:
                print(f"[WARN] webhook 非 200：{response.status_code}")

            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=f"✅ 已成功提交，共 {count} 筆日期")
            )
        except Exception as e:
            print(f"[ERROR] webhook 發送失敗：{e}")
            line_bot_api.reply_message(event.reply_token, TextSendMessage(
                text="⚠️ 系統發送失敗，請稍後再試或聯絡巧柔協助"
            ))

        clear_session(user_id)
        return True

    return False
