# handlers/support_adjust_handler.py
import requests
from linebot.models import TextSendMessage, FlexSendMessage
from utils.session_manager import get_session, set_session, clear_session
from utils.line_utils import is_trigger
import os

# ✅ Webhook URL
SUPPORT_GAS_URL = os.getenv("SUPPORT_GAS_URL", "你的GAS網址")

def handle_support_adjustment(event, user_id, text, line_bot_api):
    session = get_session(user_id) or {}

    # ✅ 啟動流程
    if is_trigger(event, ["支援醫師調診單"]):
        set_session(user_id, {"step": 1, "type": "支援醫師調診單"})
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="👨‍⚕️ 請輸入異動醫師姓名"))
        return True

    # ✅ 若不是該流程，跳過
    if session.get("type") != "支援醫師調診單":
        return False

    step = session.get("step", 0)

    # Step 1：醫師姓名
    if step == 1:
        session["doctor_name"] = text
        session["step"] = 2
        set_session(user_id, session)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="📅 請輸入原門診日期（例如：2025-07-28 上午診）"))
        return True

    # Step 2：原門診
    elif step == 2:
        session["original_date"] = text
        session["step"] = 3
        set_session(user_id, session)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="➡️ 請輸入新門診安排或休診（例如：調整至 8/5 上午診 或 休診）"))
        return True

    # Step 3：新門診
    elif step == 3:
        session["new_date"] = text
        session["step"] = 4
        set_session(user_id, session)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="📝 請輸入原因（例如：會議、返台）"))
        return True

    # Step 4：原因 & 確認畫面
    elif step == 4:
        session["reason"] = text
        session["step"] = 5
        set_session(user_id, session)

        # ✅ 顯示確認 Flex
        flex_content = {
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {"type": "text", "text": "📌 請確認調診資訊", "weight": "bold", "size": "lg"},
                    {"type": "separator", "margin": "md"},
                    {"type": "text", "text": f"醫師：{session['doctor_name']}"},
                    {"type": "text", "text": f"原門診：{session['original_date']}"},
                    {"type": "text", "text": f"異動：{session['new_date']}"},
                    {"type": "text", "text": f"原因：{session['reason']}"},
                ]
            },
            "footer": {
                "type": "box",
                "layout": "horizontal",
                "contents": [
                    {
                        "type": "button",
                        "style": "primary",
                        "color": "#00C300",
                        "action": {"type": "postback", "label": "✅ 確認送出", "data": "confirm_support"}
                    },
                    {
                        "type": "button",
                        "style": "primary",
                        "color": "#FF0000",
                        "action": {"type": "postback", "label": "❌ 取消", "data": "cancel_support"}
                    }
                ]
            }
        }

        line_bot_api.reply_message(event.reply_token, FlexSendMessage(alt_text="請確認調診申請", contents=flex_content))
        return True

    return False


def submit_support_adjustment(user_id, line_bot_api, reply_token):
    session = get_session(user_id)
    if not session:
        line_bot_api.reply_message(reply_token, TextSendMessage(text="⚠️ 沒有找到資料，請重新輸入"))
        return

    payload = {
        "doctor_name": session["doctor_name"],
        "original_date": session["original_date"],
        "new_date": session["new_date"],
        "reason": session["reason"]
    }

    try:
        response = requests.post(SUPPORT_GAS_URL, json=payload)
        if response.status_code == 200:
            line_bot_api.reply_message(reply_token, TextSendMessage(text="✅ 調診申請已送出並同步後台"))
        else:
            line_bot_api.reply_message(reply_token, TextSendMessage(text=f"❌ 送出失敗：{response.text}"))
    except Exception as e:
        line_bot_api.reply_message(reply_token, TextSendMessage(text=f"❌ 發生錯誤：{e}"))

    clear_session(user_id)
