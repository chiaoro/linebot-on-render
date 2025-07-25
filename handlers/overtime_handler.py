# handlers/overtime_handler.py
from linebot.models import TextSendMessage, FlexSendMessage
from utils.session_manager import get_session, set_session, clear_session
from utils.google_sheets import get_doctor_info
import requests
import os
import pytz
from datetime import datetime

# ✅ GAS Webhook URL（需放在 Render 的環境變數）
GAS_WEBHOOK_URL = os.getenv("OVERTIME_GAS_URL")

def handle_overtime(event, user_id, text, line_bot_api):
    """
    主加班申請流程
    """
    session = get_session(user_id) or {}

    # ✅ 啟動加班申請
    if text == "加班申請":
        set_session(user_id, {"step": 1})
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請輸入加班日期（格式：YYYY-MM-DD）"))
        return True

    # ✅ Step 1：輸入日期
    if session.get("step") == 1:
        set_session(user_id, {"step": 2, "date": text})
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請輸入加班時間（格式：HH:MM-HH:MM）"))
        return True

    # ✅ Step 2：輸入時間
    if session.get("step") == 2:
        set_session(user_id, {"step": 3, "date": session["date"], "time": text})
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請輸入加班事由"))
        return True

    # ✅ Step 3：輸入事由並顯示確認卡片
    if session.get("step") == 3:
        date = session["date"]
        time_range = session["time"]
        reason = text

        # ✅ 轉換日期 → 民國年格式
        roc_year = int(date.split("-")[0]) - 1911
        roc_date = f"{roc_year}年{date.split('-')[1]}月{date.split('-')[2]}日"

        # ✅ 存回 Session
        set_session(user_id, {
            "step": 4,
            "date": date,
            "time": time_range,
            "reason": reason
        })

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
                    {"type": "text", "text": f"時間：{time_range}", "margin": "sm"},
                    {"type": "text", "text": f"事由：{reason}", "margin": "sm"}
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
    # 取出暫存資料
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
    if not doctor_info:
        doctor_name = "未知醫師"
        dept = "未知科別"
    else:
        doctor_name, dept = doctor_info  # ✅ tuple 解構

    # ✅ 產生台灣時間戳記
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
            line_bot_api.reply_message(reply_token, TextSendMessage(text="✅ 加班申請已送出並同步至後台"))
        else:
            line_bot_api.reply_message(reply_token, TextSendMessage(text=f"❌ 送出失敗：{response.text}"))
    except Exception as e:
        line_bot_api.reply_message(reply_token, TextSendMessage(text=f"❌ 發生錯誤：{e}"))

    # ✅ 清除 Session
    clear_session(user_id)
