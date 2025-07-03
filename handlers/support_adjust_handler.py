# handlers/support_adjust_handler.py

import requests
from linebot.models import TextSendMessage, FlexSendMessage
from utils.session_manager import get_session, set_session, clear_session
from utils.line_utils import is_trigger  # ✅ 你自己的觸發字串判斷工具
from utils.support_bubble import get_support_adjustment_bubble  # ✅ 建議分出去

def handle_support_adjustment(event, user_id, text, line_bot_api):
    # ✅ 啟動流程
    if is_trigger(event, ["支援醫師調診單"]):
        set_session(user_id, {"step": 0, "type": "支援醫師調診單"})
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="👨‍⚕️ 請問需異動門診醫師姓名？")
        )
        return True

    # ✅ 若非該流程則跳過
    session = get_session(user_id)
    if session.get("type") != "支援醫師調診單":
        return False

    step = session.get("step", 0)

    # Step 0：醫師姓名
    if step == 0:
        session["doctor_name"] = text
        session["step"] = 1
        line_bot_api.reply_message(user_id, TextSendMessage(text="📅 請問原本門診是哪一天？（例如：5/6 上午診）"))

    # Step 1：原門診日期
    elif step == 1:
        session["original_date"] = text
        session["step"] = 2
        line_bot_api.reply_message(user_id, TextSendMessage(text="⚙️ 請問您希望如何處理？（例如：休診、調整至5/16 上午診）"))

    # Step 2：新門診安排
    elif step == 2:
        session["new_date"] = text
        session["step"] = 3
        line_bot_api.reply_message(user_id, TextSendMessage(text="📝 最後，請輸入原因（例如：需返台、會議）"))

    # Step 3：填寫原因並送出 webhook
    elif step == 3:
        session["reason"] = text
        send_to_webhook_and_reply(session, user_id, line_bot_api)
        clear_session(user_id)
        return True

    set_session(user_id, session)
    return True


def send_to_webhook_and_reply(session, user_id, line_bot_api):
    webhook_url = "https://script.google.com/macros/s/AKfycbwLGVRboA0UDU_HluzYURY6Rw4Y8PKMfbclmbWdqpx7MAs37o18dqPkAssU1AuZrC8hxQ/exec"

    payload = {
        "user_id": user_id,
        "request_type": "支援醫師調診單",
        "doctor_name": session["doctor_name"],
        "original_date": session["original_date"],
        "new_date": session["new_date"],
        "reason": session["reason"]
    }

    try:
        requests.post(webhook_url, json=payload)
        bubble = get_support_adjustment_bubble(
            doctor_name=session["doctor_name"],
            original=session["original_date"],
            method=session["new_date"],
            reason=session["reason"]
        )
        line_bot_api.push_message(
            user_id,
            FlexSendMessage(alt_text="支援醫師調診單已送出", contents=bubble)
        )
    except Exception as e:
        print("❌ webhook 發送失敗：", str(e))
        line_bot_api.push_message(user_id, TextSendMessage(
            text="⚠️ 系統提交失敗，請稍後再試或聯絡巧柔"
        ))
