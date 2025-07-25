# handlers/overtime_handler.py
from linebot.models import TextSendMessage, FlexSendMessage
from utils.session_manager import get_session, set_session, clear_session
from utils.google_sheets import get_doctor_info
import requests
import os
from datetime import datetime

# ✅ API URL（Render 伺服器的網址）
API_URL = os.getenv("API_BASE_URL", "https://linebot-on-render.onrender.com/api/overtime")

def handle_overtime(event, user_id, text, line_bot_api):
    session = get_session(user_id)

    # ✅ 啟動流程
    if text == "加班申請":
        set_session(user_id, {"step": 1, "type": "overtime"})
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="請輸入加班日期（格式：YYYY-MM-DD）")
        )
        return True

    # ✅ 確認是否在流程中
    if not session or session.get("type") != "overtime":
        return False

    step = session.get("step", 1)

    # Step 1：輸入日期
    if step == 1:
        session["date"] = text
        session["step"] = 2
        set_session(user_id, session)
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="請輸入加班時間（格式：HH:MM-HH:MM）")
        )
        return True

    # Step 2：輸入時間
    if step == 2:
        session["time"] = text
        session["step"] = 3
        set_session(user_id, session)
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="請輸入加班事由")
        )
        return True

    # Step 3：輸入事由並顯示確認畫面
    if step == 3:
        session["reason"] = text

        # ✅ 查詢醫師姓名與科別
        doctor_info = get_doctor_info(
            "https://docs.google.com/spreadsheets/d/1fHf5XlbvLMd6ytAh_t8Bsi5ghToiQHZy1NlVfEG7VIo/edit",
            user_id
        )
        doctor_name = doctor_info.get("姓名", "未知醫師")
        doctor_dept = doctor_info.get("科別", "未填科別")

        # ✅ 保存 session
        session["doctor_name"] = doctor_name
        session["doctor_dept"] = doctor_dept
        set_session(user_id, session)

        # ✅ Flex 確認畫面
        bubble = {
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {"type": "text", "text": "📋 請確認加班申請", "weight": "bold", "size": "lg"},
                    {"type": "text", "text": f"日期：{session['date']}", "margin": "md"},
                    {"type": "text", "text": f"時間：{session['time']}", "margin": "md"},
                    {"type": "text", "text": f"事由：{session['reason']}", "margin": "md"}
                ]
            },
            "footer": {
                "type": "box",
                "layout": "horizontal",
                "contents": [
                    {
                        "type": "button",
                        "style": "primary",
                        "color": "#1DB446",
                        "action": {"type": "postback", "label": "✅ 確認送出", "data": "confirm_overtime"}
                    },
                    {
                        "type": "button",
                        "style": "primary",
                        "color": "#FF3B30",
                        "action": {"type": "postback", "label": "❌ 取消", "data": "cancel_overtime"}
                    }
                ]
            }
        }

        line_bot_api.reply_message(
            event.reply_token,
            FlexSendMessage(alt_text="確認加班申請", contents=bubble)
        )
        return True

    return False


# ✅ 提交資料到 API
def submit_overtime(user_id, line_bot_api, reply_token):
    session = get_session(user_id)
    if not session:
        line_bot_api.reply_message(reply_token, TextSendMessage(text="❌ 找不到申請資料，請重新開始"))
        return

    # ✅ 準備資料
    data = {
        "name": session["doctor_name"],
        "dept": session["doctor_dept"],
        "date": session["date"],
        "time": session["time"],
        "reason": session["reason"]
    }

    try:
        res = requests.post(API_URL, json=data)
        if res.status_code == 200:
            line_bot_api.reply_message(reply_token, TextSendMessage(text="✅ 加班申請已送出"))
        else:
            line_bot_api.reply_message(reply_token, TextSendMessage(text=f"❌ 送出失敗：{res.text}"))
    except Exception as e:
        line_bot_api.reply_message(reply_token, TextSendMessage(text=f"❌ 發生錯誤：{e}"))
    finally:
        clear_session(user_id)
