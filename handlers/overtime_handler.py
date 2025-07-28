# handlers/overtime_handler.py
from linebot.models import TextSendMessage, FlexSendMessage
from utils.session_manager import get_session, set_session, clear_session
from utils.google_sheets import get_doctor_info
import requests
import os
import pytz
from datetime import datetime

# ✅ 環境變數（Render 設定）
OVERTIME_GAS_URL = os.getenv("OVERTIME_GAS_URL")  # 請在 Render 設定

def handle_overtime(event, user_id, text, line_bot_api):
    """
    加班申請主流程
    """
    session = get_session(user_id) or {}

    # ✅ Step 0：啟動流程
    if text == "加班申請" and not session:
        set_session(user_id, {"step": 1, "type": "加班申請"})
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請輸入加班日期（格式：YYYY-MM-DD）"))
        return True

    # ✅ 僅處理該流程
    if session.get("type") != "加班申請":
        return False

    # ✅ Step 1：輸入日期
    if session.get("step") == 1:
        session["step"] = 2
        session["date"] = text
        set_session(user_id, session)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請輸入加班時間（格式：HH:MM-HH:MM）"))
        return True

    # ✅ Step 2：輸入時間
    if session.get("step") == 2:
        session["step"] = 3
        session["time"] = text
        set_session(user_id, session)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請輸入加班事由（需詳述，例如：完成病例、會議）"))
        return True

    # ✅ Step 3：輸入原因並顯示確認卡片
    if session.get("step") == 3:
        session["reason"] = text
        session["step"] = 4
        set_session(user_id, session)

        # ✅ 民國日期
        roc_year = int(session["date"].split("-")[0]) - 1911
        roc_date = f"{roc_year}年{session['date'].split('-')[1]}月{session['date'].split('-')[2]}日"

        # ✅ Flex Message（不顯示姓名 & 科別）
        flex_content = {
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {"type": "text", "text": "📝 請確認加班申請", "weight": "bold", "size": "lg"},
                    {"type": "separator", "margin": "md"},
                    {"type": "text", "text": f"日期：{roc_date}", "margin": "sm"},
                    {"type": "text", "text": f"時間：{session['time']}", "margin": "sm"},
                    {"type": "text", "text": f"事由：{session['reason']}", "margin": "sm"}
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
                        "action": {"type": "postback", "label": "✅ 確認送出", "data": "confirm_overtime"}
                    },
                    {
                        "type": "button",
                        "style": "primary",
                        "color": "#FF0000",
                        "action": {"type": "postback", "label": "❌ 取消", "data": "cancel_overtime"}
                    }
                ]
            }
        }

        line_bot_api.reply_message(event.reply_token, FlexSendMessage(alt_text="請確認加班申請", contents=flex_content))
        return True

    return False


def submit_overtime(user_id, line_bot_api, reply_token):
    """
    ✅ 確認送出後，將資料送到 Google Apps Script + 試算表
    """
    session = get_session(user_id)
    if not session:
        line_bot_api.reply_message(reply_token, TextSendMessage(text="⚠️ 沒有找到加班資料，請重新輸入"))
        return

    date = session.get("date")
    time_range = session.get("time")
    reason = session.get("reason")

    # ✅ 取得醫師姓名與科別
    doctor_info = get_doctor_info(
        "https://docs.google.com/spreadsheets/d/1fHf5XlbvLMd6ytAh_t8Bsi5ghToiQHZy1NlVfEG7VIo/edit",
        user_id
    )
    if doctor_info:
        doctor_name, dept = doctor_info
    else:
        doctor_name = "未知"
        dept = "未知"

    # ✅ 台灣時間戳記
    tz = pytz.timezone('Asia/Taipei')
    timestamp = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")

    # ✅ 呼叫 GAS Webhook
    try:
        response = requests.post(OVERTIME_GAS_URL, json={
            "timestamp": timestamp,
            "dept": dept,
            "name": doctor_name,
            "date": date,
            "time": time_range,
            "reason": reason
        })
        if response.status_code == 200:
            line_bot_api.reply_message(reply_token, TextSendMessage(text="✅ 加班申請已送出並同步後台"))
        else:
            line_bot_api.reply_message(reply_token, TextSendMessage(text=f"❌ 送出失敗：{response.text}"))
    except Exception as e:
        line_bot_api.reply_message(reply_token, TextSendMessage(text=f"❌ 發生錯誤：{e}"))

    clear_session(user_id)
