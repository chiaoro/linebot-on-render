# handlers/overtime_handler.py
import os
import json
import requests
from linebot.models import TextSendMessage, FlexSendMessage
from utils.session_manager import get_session, set_session, clear_session
from utils.google_sheets import get_doctor_info
from datetime import datetime
import pytz

# ✅ Google Sheet URL
DOCTOR_SHEET_URL = "https://docs.google.com/spreadsheets/d/1fHf5XlbvLMd6ytAh_t8Bsi5ghToiQHZy1NlVfEG7VIo/edit"

# ✅ API endpoint
OVERTIME_API_URL = "https://linebot-on-render.onrender.com/api/overtime"  # 你的 Flask API URL

def handle_overtime(event, user_id, text, line_bot_api):
    session = get_session(user_id)

    # ✅ 啟動流程
    if text == "加班申請":
        set_session(user_id, {"step": 1, "type": "overtime", "data": {}})
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請輸入加班日期（格式：YYYY-MM-DD）"))
        return True

    # ✅ 如果不是加班流程，直接跳過
    if not session or session.get("type") != "overtime":
        return False

    step = session.get("step", 1)
    data = session.get("data", {})

    # ✅ Step 1：輸入加班日期
    if step == 1:
        data["date"] = text
        session["step"] = 2
        session["data"] = data
        set_session(user_id, session)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請輸入加班時間（格式：HH:MM-HH:MM）"))
        return True

    # ✅ Step 2：輸入加班時間
    if step == 2:
        data["time"] = text
        session["step"] = 3
        session["data"] = data
        set_session(user_id, session)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請輸入加班事由"))
        return True

    # ✅ Step 3：輸入加班事由，顯示確認 Flex
    if step == 3:
        data["reason"] = text
        session["data"] = data
        set_session(user_id, session)

        # ✅ 取得醫師姓名與科別
        doctor_info = get_doctor_info(DOCTOR_SHEET_URL, user_id)
        doctor_name, department = doctor_info if doctor_info else ("未知", "醫療部")

        # ✅ 日期轉換格式 (民國年)
        date_parts = data["date"].split("-")
        year = int(date_parts[0]) - 1911
        formatted_date = f"{year}年 {date_parts[1]}月{date_parts[2]}日"

        # ✅ 建立 Flex 確認畫面
        flex_content = {
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {"type": "text", "text": "📝 請確認加班申請", "weight": "bold", "size": "lg", "margin": "md"},
                    {"type": "separator", "margin": "md"},
                    {"type": "text", "text": f"醫師：{doctor_name}", "size": "md", "margin": "sm"},
                    {"type": "text", "text": f"科別：{department}", "size": "md", "margin": "sm"},
                    {"type": "text", "text": f"日期：{formatted_date}", "size": "md", "margin": "sm"},
                    {"type": "text", "text": f"時間：{data['time']}", "size": "md", "margin": "sm"},
                    {"type": "text", "text": f"事由：{data['reason']}", "size": "md", "margin": "sm"},
                    {"type": "separator", "margin": "md"},
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "spacing": "md",
                        "contents": [
                            {
                                "type": "button",
                                "style": "primary",
                                "color": "#00C300",
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
                ]
            }
        }

        line_bot_api.reply_message(
            event.reply_token,
            FlexSendMessage(alt_text="請確認加班申請", contents=flex_content)
        )
        return True

    return False


def submit_overtime(user_id, line_bot_api, reply_token):
    session = get_session(user_id)
    if not session:
        line_bot_api.reply_message(reply_token, TextSendMessage("❌ 找不到加班資料，請重新輸入"))
        return

    date = session.get("date")
    time_range = session.get("time")
    reason = session.get("reason")

    # ✅ 加入台灣時間
    from datetime import datetime
    import pytz
    tz = pytz.timezone('Asia/Taipei')
    timestamp = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")

    # ✅ 取得醫師姓名與科別
    from utils.google_sheets import get_doctor_info
    doctor_name, doctor_dept = get_doctor_info(DOCTOR_SHEET_URL, user_id)
    doctor_name = doctor_name or "未知"
    doctor_dept = doctor_dept or "未填科別"

    # ✅ 發送到 Google Apps Script
    payload = {
        "timestamp": timestamp,
        "name": doctor_name,
        "dept": doctor_dept,
        "date": date,
        "time": time_range,
        "reason": reason
    }

    try:
        response = requests.post(GAS_WEBHOOK_URL, json=payload)
        response.raise_for_status()
        line_bot_api.reply_message(reply_token, TextSendMessage("✅ 加班申請已送出"))
        clear_session(user_id)
    except Exception as e:
        line_bot_api.reply_message(reply_token, TextSendMessage(f"❌ 送出失敗：{e}"))
