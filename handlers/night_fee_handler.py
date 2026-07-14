# handlers/night_fee_handler.py

from linebot.models import FlexSendMessage, TextSendMessage
from utils.session_manager import get_session, set_session, clear_session
from utils.date_parser import expand_date_range
import requests
import re

def handle_night_fee(event, user_id, text, line_bot_api):
    session = get_session(user_id)

    # ✅ 清除其他流程殘留的 session（非夜點費流程時）
    if session.get("type") not in [None, "夜點費申請"]:
        clear_session(user_id)
        session = {}

    # ✅ 開始流程：點選「夜點費申請」按鈕
    if text == "夜點費申請":
        set_session(user_id, {
            "type": "夜點費申請",
            "status": "awaiting_dates"
        })

        bubble = {
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {"type": "text", "text": "🌙 夜點費申請", "weight": "bold", "size": "lg"},
                    {"type": "text", "text": "請輸入值班日期（可輸入區間）", "margin": "md"},
                    {"type": "text", "text": "範例：\n5、6、16、17、18、25、27、31", "size": "sm", "color": "#888888", "margin": "md"}
                ]
            }
        }
        line_bot_api.reply_message(event.reply_token, FlexSendMessage(alt_text="🌙 夜點費申請", contents=bubble))
        return True

    # ✅ 使用者已輸入日期（夜點費流程中）
    if session.get("type") == "夜點費申請" and session.get("status") == "awaiting_dates":
        raw_input = event.message.text.strip()

        try:
            expanded = expand_date_range(raw_input)
            count = len(expanded)

            # ✅ 送出至 webhook
            webhook_url = "https://script.google.com/macros/s/AKfycbxOKltHGgoz05CKpTJIu4kFdzzmKd9bzL7bT5LOqYu5Lql6iaTlgFI9_lHwqFQFV8-J/exec"
            payload = {"user_id": user_id, "日期": raw_input}
            response = requests.post(webhook_url, json=payload, timeout=10)

            print("📡 webhook 回傳：", response.status_code, response.text)

            # ✅ 回覆成功訊息
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=f"✅ 已成功提交，共 {count} 筆日期")
            )

        except Exception as e:
            print(f"[ERROR] 日期處理失敗：{e}")
            line_bot_api.reply_message(event.reply_token, TextSendMessage(
                text="⚠️ 日期格式錯誤或提交失敗，請再試一次或聯絡巧柔協助"
            ))

        # ✅ 清除流程狀態，確保不跳入其他 handler
        clear_session(user_id)
        return True

    return False
