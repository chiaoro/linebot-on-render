# handlers/overtime_handler.py
from linebot.models import TextSendMessage, FlexSendMessage
import requests
import os
from utils.session_manager import get_session, set_session, clear_session
from utils.google_sheets import get_doctor_info

API_URL = os.getenv("API_BASE_URL", "https://linebot-on-render.onrender.com")

def handle_overtime(event, user_id, text, line_bot_api):
    session = get_session(user_id)

    # ✅ Step 0：啟動流程
    if text == "加班申請":
        set_session(user_id, {"step": 1, "type": "overtime"})
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="請輸入加班日期（格式：YYYY-MM-DD）")
        )
        return True

    # ✅ 非加班流程則跳過
    if session.get("type") != "overtime":
        return False

    step = session.get("step", 1)

    # ✅ Step 1：輸入日期
    if step == 1:
        set_session(user_id, {**session, "date": text, "step": 2})
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="請輸入加班時間（格式：HH:MM-HH:MM）")
        )
        return True

    # ✅ Step 2：輸入時間
    if step == 2:
        set_session(user_id, {**session, "time": text, "step": 3})
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="請輸入加班事由")
        )
        return True

    # ✅ Step 3：輸入原因並顯示確認 Flex
    if step == 3:
        session["reason"] = text

        # ✅ 取得醫師資訊
        doctor_info = get_doctor_info(
            "https://docs.google.com/spreadsheets/d/1fHf5XlbvLMd6ytAh_t8Bsi5ghToiQHZy1NlVfEG7VIo/edit",
            user_id
        )

        # ✅ 判斷回傳格式
        if isinstance(doctor_info, tuple):
            doctor_name, doctor_dept = doctor_info
        else:
            doctor_name = doctor_info.get("姓名", "未知醫師")
            doctor_dept = doctor_info.get("科別", "未填科別")

        session["doctor_name"] = doctor_name
        session["doctor_dept"] = doctor_dept
        set_session(user_id, {**session, "step": 4})

        # ✅ Flex 確認卡片
        flex_content = {
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {"type": "text", "text": "📄 請確認加班申請", "weight": "bold", "size": "lg"},
                    {"type": "separator", "margin": "md"},
                    {"type": "box", "layout": "vertical", "margin": "md", "contents": [
                        {"type": "text", "text": f"醫師：{doctor_name} ({doctor_dept})"},
                        {"type": "text", "text": f"日期：{session['date']}"},
                        {"type": "text", "text": f"時間：{session['time']}"},
                        {"type": "text", "text": f"事由：{session['reason']}"}
                    ]},
                    {"type": "separator", "margin": "md"},
                    {"type": "box", "layout": "horizontal", "spacing": "md", "margin": "md", "contents": [
                        {
                            "type": "button",
                            "style": "primary",
                            "color": "#28a745",
                            "action": {
                                "type": "postback",
                                "label": "✅ 確認送出",
                                "data": "confirm_overtime"
                            }
                        },
                        {
                            "type": "button",
                            "style": "secondary",
                            "color": "#dc3545",
                            "action": {
                                "type": "postback",
                                "label": "❌ 取消",
                                "data": "cancel_overtime"
                            }
                        }
                    ]}
                ]
            }
        }

        line_bot_api.reply_message(
            event.reply_token,
            FlexSendMessage(alt_text="請確認加班申請", contents=flex_content)
        )
        return True

    return False


# ✅ PostbackEvent：處理確認 / 取消
def handle_overtime_postback(event, user_id, line_bot_api):
    session = get_session(user_id)
    data = event.postback.data

    if session.get("type") != "overtime":
        return False

    if data == "confirm_overtime":
        try:
            # ✅ 呼叫 API 寫入 Google Sheet
            payload = {
                "name": session.get("doctor_name", "未知醫師"),
                "dept": session.get("doctor_dept", "未填科別"),
                "date": session["date"],
                "time": session["time"],
                "reason": session["reason"]
            }
            res = requests.post(f"{API_URL}/api/overtime", json=payload)
            if res.status_code == 200:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text="✅ 加班申請已送出！")
                )
            else:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=f"❌ 送出失敗：{res.text}")
                )
        except Exception as e:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=f"❌ 發生錯誤：{str(e)}")
            )
        finally:
            clear_session(user_id)
        return True

    elif data == "cancel_overtime":
        clear_session(user_id)
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="❌ 已取消加班申請")
        )
        return True

    return False
