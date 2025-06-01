from linebot.models import TextSendMessage, FlexSendMessage
import re
import requests
from utils.session_manager import user_sessions
from utils.line_utils import is_trigger
from utils.flex_templates import get_duty_swap_bubble, get_duty_proxy_bubble


def handle_duty_message(event, user_id, text, line_bot_api):
    # ✅ 啟動流程：值班調換或代理
    if is_trigger(event, ["值班調換", "值班代理"]):
        action_type = "值班調換" if "調換" in (event.message.text if event.type == "message" else event.postback.data) else "值班代理"
        user_sessions[user_id] = {"step": 0, "type": action_type}
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="🧑‍⚕️ 請輸入您的姓名"))
        return True

    # ✅ 後續流程
    if user_id in user_sessions:
        session = user_sessions[user_id]
        step = session.get("step")

        if step is None:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="⚠️ 請先點選【值班調換】或【值班代理】開始流程"))
            return True

        # Step 0: 醫師姓名
        if step == 0:
            session["original_doctor"] = text
            session["step"] = 1
            line_bot_api.push_message(user_id, TextSendMessage(text="🗕️ 請輸入原值班內容（格式：6/15 骨科會討）"))
            return True

        # Step 1: 原值班內容或日期
        elif step == 1:
            if session["type"] == "值班調換":
                match = re.match(r"(\d{1,2}/\d{1,2})\s*(.+)", text)
                if match:
                    session["original_date"] = match.group(1)
                    session["shift_type"] = match.group(2).strip()
                    session["step"] = 2
                    line_bot_api.push_message(user_id, TextSendMessage(text="🔁 請輸入對調醫師與調換日期（例如：李大華 5/20）"))
                else:
                    line_bot_api.push_message(user_id, TextSendMessage(text="⚠️ 請輸入正確格式，例如：6/15 骨科會討"))
                return True
            else:
                session["original_date"] = text
                session["shift_type"] = "未指定"
                session["step"] = 2
                line_bot_api.push_message(user_id, TextSendMessage(text="🙆‍♂️ 請輸入代理醫師姓名"))
                return True

        # Step 2: 對調醫師與日期 或 代理醫師姓名
        elif step == 2:
            if session["type"] == "值班調換":
                parts = text.split()
                if len(parts) >= 2:
                    session["target_doctor"] = parts[0]
                    session["swap_date"] = parts[1]
                    session["step"] = 3
                    line_bot_api.push_message(user_id, TextSendMessage(text="📝 請輸入調換原因"))
                else:
                    line_bot_api.push_message(user_id, TextSendMessage(text="⚠️ 格式錯誤，請輸入：李大華 5/20"))
            else:
                session["proxy_doctor"] = text
                session["step"] = 3
                line_bot_api.push_message(user_id, TextSendMessage(text="📝 請輸入代理原因"))
            return True

        # Step 3: 理由並送出表單
        elif step == 3:
            session["reason"] = text
            webhook_url = "https://script.google.com/macros/s/YOUR_WEBHOOK_URL/exec"  # 請替換為實際網址

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
                requests.post(webhook_url, json=payload)

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

                line_bot_api.push_message(
                    user_id,
                    FlexSendMessage(alt_text=f"{session['type']}通知", contents=bubble)
                )

            except Exception as e:
                print("❌ webhook 發送失敗：", str(e))
                line_bot_api.push_message(user_id, TextSendMessage(
                    text="⚠️ 系統提交失敗，請稍後再試或聯絡巧柔"
                ))

            del user_sessions[user_id]
            return True

    return False
