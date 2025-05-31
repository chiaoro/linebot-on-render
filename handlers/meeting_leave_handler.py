# handlers/meeting_leave_handler.py
import requests
from linebot.models import TextSendMessage
from utils.user_binding import user_states

def handle_meeting_leave(event, user_id, text, line_bot_api):
    if user_states.get(user_id, {}).get("flow") != "meeting_leave" and text != "我要請假":
        return False

    if text == "我要請假":
        user_states[user_id] = {"flow": "meeting_leave", "step": 1}
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="🧑‍⚕️ 請輸入您的姓名"))
        return True

    state = user_states.get(user_id, {})
    step = state.get("step")

    if step == 1:
        state["name"] = text.strip()
        state["step"] = 2
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="📅 請輸入請假日期（例如：5/15）"))
        return True

    if step == 2:
        state["date"] = text.strip()
        state["step"] = 3
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="✏️ 請輸入請假原因"))
        return True

    if step == 3:
        state["reason"] = text.strip()

        payload = {
            "user_id": user_id,
            "姓名": state["name"],
            "日期": state["date"],
            "原因": state["reason"]
        }

        try:
            webhook_url = "https://script.google.com/macros/s/你的_webhook_url/exec"
            response = requests.post(webhook_url, json=payload)
            if response.status_code == 200:
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="✅ 請假申請已送出"))
            else:
                raise Exception(response.text)
        except Exception as e:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="⚠️ 系統錯誤，請稍後再試"))
        
        del user_states[user_id]
        return True

    return False
