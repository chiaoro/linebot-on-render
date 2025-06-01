from linebot.models import TextSendMessage, FlexSendMessage
import re
import requests
from utils.session_manager import get_session, set_session, clear_session
from utils.line_utils import is_trigger
from utils.flex_templates import get_duty_swap_bubble, get_duty_proxy_bubble

def handle_duty_message(event, user_id, text, line_bot_api):
    session = get_session(user_id)

    # ✅ 啟動流程
    if is_trigger(event, ["值班調換", "值班代理"]):
        duty_type = "值班調換" if "調換" in text else "值班代理"
        set_session(user_id, {"type": duty_type, "status": "awaiting_name"})
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="🧑‍⚕️ 請輸入您的姓名"))
        return True

    # ✅ 僅處理 duty 流程，避免干擾其他流程
    if session.get("type") not in ["值班調換", "值班代理"]:
        return False

    status = session.get("status")

    # Step 0：輸入姓名
    if status == "awaiting_name":
        session["original_doctor"] = text
        session["status"] = "awaiting_original_info"
        set_session(user_id, session)
        line_bot_api.push_message(user_id, TextSendMessage(text="請輸入原值班內容（格式：6/15 骨科會診）"))
        return True

    # Step 1：原值班內容
    if status == "awaiting_original_info":
        if session["type"] == "值班調換":
            match = re.match(r"(\d{1,2}/\d{1,2})\s*(.+)", text)
            if match:
                session["original_date"] = match.group(1)
                session["shift_type"] = match.group(2).strip()
                session["status"] = "awaiting_swap_info"
                set_session(user_id, session)
                line_bot_api.push_message(user_id, TextSendMessage(text="🔁 請輸入對調醫師與調換日期（例如：李大華 5/20）"))
            else:
                line_bot_api.push_message(user_id, TextSendMessage(text="⚠️ 請輸入正確格式，例如：6/15 骨科會討"))
        else:
            session["original_date"] = text
            session["shift_type"] = "未指定"
            session["status"] = "awaiting_proxy_name"
            set_session(user_id, session)
            line_bot_api.push_message(user_id, TextSendMessage(text="🙆‍♂️ 請輸入代理醫師姓名"))
        return True

    # Step 2：對調醫師與日期 or 代理醫師姓名
    if status in ["awaiting_swap_info", "awaiting_proxy_name"]:
        if session["type"] == "值班調換":
            parts = text.split()
            if len(parts) >= 2:
                session["target_doctor"] = parts[0]
                session["swap_date"] = parts[1]
                session["status"] = "awaiting_reason"
                set_session(user_id, session)
                line_bot_api.push_message(user_id, TextSendMessage(text="📝 請輸入調換原因"))
            else:
                line_bot_api.push_message(user_id, TextSendMessage(text="⚠️ 格式錯誤，請輸入：李大華 5/20"))
        else:
            session["proxy_doctor"] = text
            session["status"] = "awaiting_reason"
            set_session(user_id, session)
            line_bot_api.push_message(user_id, TextSendMessage(text="📝 請輸入代理原因"))
        return True

    # Step 3：原因並提交
    if status == "awaiting_reason":
        session["reason"] = text

        payload = {
            "request_type": session.get("type", ""),
            "original_doctor": session.get("original_doctor", ""),
            "original_date": session.get("original_date", ""),
            "shift_type": session.get("shift_type", ""),
            "reason": session.get("reason", "")
        }

        if session["type"] == "值班調換":
            payload.update({
                "target_doctor": session.get("target_doctor", ""),
                "swap_date": session.get("swap_date", "")
            })
        else:
            payload["proxy_doctor"] = session.get("proxy_doctor", "")

        try:
            # ✅ 替換成你的 webhook
            webhook_url = "https://script.google.com/macros/s/AKfycbxonJeiBfqvPQnPyApWAc_3B8mwvC9b1lA6B4E_rQLIULdPzifcAYzYH5c1PrWdEHl1Tw/exec"
            requests.post(webhook_url, data=payload)

            bubble = (
                get_duty_swap_bubble(
                    shift_type=session.get("shift_type", ""),
                    original_doctor=session.get("original_doctor", ""),
                    original_date=session.get("original_date", ""),
                    target_doctor=session.get("target_doctor", ""),
                    swap_date=session.get("swap_date", ""),
                    reason=session.get("reason", "")
                ) if session["type"] == "值班調換" else
                get_duty_proxy_bubble(
                    shift_type=session.get("shift_type", ""),
                    original_doctor=session.get("original_doctor", ""),
                    original_date=session.get("original_date", ""),
                    proxy_doctor=session.get("proxy_doctor", ""),
                    reason=session.get("reason", "")
                )
            )

            line_bot_api.push_message(user_id, FlexSendMessage(
                alt_text=f"{session['type']}通知", contents=bubble
            ))

        except Exception as e:
            print("❌ webhook 發送失敗：", str(e))
            line_bot_api.push_message(user_id, TextSendMessage(
                text="⚠️ 系統提交失敗，請稍後再試或聯絡巧柔"
            ))

        clear_session(user_id)
        return True

    return False
