# handlers/night_fee_handler.py

from linebot.models import FlexSendMessage, TextSendMessage
from utils.session_manager import get_session, set_session, clear_session
from utils.date_parser import expand_date_range
import requests

def handle_night_fee(event, user_id, text, line_bot_api):
    session = get_session(user_id)

    # ✅ 防止其他流程的 user_sessions 影響
    if session.get("type") and session.get("type") != "夜點費申請":
        clear_session(user_id)
        session = {}

    # ✅ 使用者輸入「夜點費申請」
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
        line_bot_api.reply_message(event.reply_token, FlexSendMessage(alt_text="🌙 夜點費申請", contents=bubble))
        return True

    # ✅ 處理使用者輸入日期
    if session.get("type") == "夜點費申請" and session.get("step") == 1:
        raw_input = event.message.text.strip()
        try:
            expanded = expand_date_range(raw_input)
            count = len(expanded)

            webhook_url = "https://script.google.com/macros/s/AKfycbxOKltHGgoz05CKpTJIu4kFdzzmKd9bzL7bT5LOqYu5Lql6iaTlgFI9_lHwqFQFV8-J/exec"
            payload = {"user_id": user_id, "日期": raw_input}
            response = requests.post(webhook_url, json=payload)

            print("📡 webhook 回傳：", response.status_code, response.text)

            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=f"✅ 已成功提交，共 {count} 筆日期")
            )
        except Exception as e:
            print(f"[ERROR] 發送失敗：{e}")
            line_bot_api.reply_message(event.reply_token, TextSendMessage(
                text="⚠️ 日期格式錯誤或提交失敗，請再試一次或聯絡巧柔"
            ))

        clear_session(user_id)
        return True

    return False
