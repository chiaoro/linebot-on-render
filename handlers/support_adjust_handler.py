# handlers/support_adjust_handler.py
import requests
from linebot.models import TextSendMessage, FlexSendMessage
from utils.session_manager import get_session, set_session, clear_session
from utils.line_utils import is_trigger
from utils.support_bubble import get_support_adjustment_bubble  # 如果要 Flex

# ✅ Google Apps Script Webhook
SUPPORT_ADJUST_WEBHOOK = "https://script.google.com/macros/s/AKfycbwLGVRboA0UDU_HluzYURY6Rw4Y8PKMfbclmbWdqpx7MAs37o18dqPkAssU1AuZrC8hxQ/exec"

def handle_support_adjustment(event, user_id, text, line_bot_api):
    """
    支援醫師調診單流程（完全獨立，避免與其他流程衝突）
    """
    session = get_session(user_id) or {}

    # ✅ 非本流程且不是啟動指令 → 跳過
    if session.get("type") and session.get("type") != "支援醫師調診單" and not is_trigger(event, ["支援醫師調診單"]):
        return False

    # ✅ 啟動流程
    if text == "支援醫師調診單":
        set_session(user_id, {"type": "支援醫師調診單", "step": 1})
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="👨‍⚕️ 請輸入需異動門診醫師姓名"))
        return True

    # ✅ Step 1：醫師姓名
    if session.get("step") == 1:
        session["doctor_name"] = text.strip()
        session["step"] = 2
        set_session(user_id, session)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="📅 請輸入原門診日期與時段（例如：2025-08-05 上午診）"))
        return True

    # ✅ Step 2：原門診安排
    if session.get("step") == 2:
        session["original_date"] = text.strip()
        session["step"] = 3
        set_session(user_id, session)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="🔄 請輸入新安排（例如：調整至 2025-08-10 下午診，或輸入『休診』）"))
        return True

    # ✅ Step 3：新門診或休診後 → 要求原因
    if session.get("step") == 3:
        session["new_plan"] = text.strip()
        session["step"] = 4
        set_session(user_id, session)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="📝 請輸入調整原因（例如：開會、請假）"))
        return True

    # ✅ Step 4：原因 + 送出 webhook
    if session.get("step") == 4:
        session["reason"] = text.strip()

        # ✅ 呼叫 Google Apps Script
        payload = {
            "user_id": user_id,
            "doctor_name": session.get("doctor_name"),
            "original_date": session.get("original_date"),
            "new_plan": session.get("new_plan"),
            "reason": session.get("reason"),
            "request_type": "支援醫師調診單"
        }

        try:
            requests.post(SUPPORT_ADJUST_WEBHOOK, json=payload)

            # ✅ Flex Message 確認送出
            bubble = get_support_adjustment_bubble(
                doctor_name=session["doctor_name"],
                original=session["original_date"],
                method=session["new_plan"],
                reason=session["reason"]
            )
            line_bot_api.reply_message(event.reply_token, FlexSendMessage(alt_text="✅ 支援醫師調診單已送出", contents=bubble))

        except Exception as e:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"❌ 發送失敗：{e}"))

        # ✅ 清除 Session
        clear_session(user_id)
        return True

    return False
