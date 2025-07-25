# handlers/overtime_handler.py

from linebot.models import TextSendMessage, FlexSendMessage, PostbackEvent
from utils.session_manager import get_session, set_session, clear_session
from utils.google_sheets import get_doctor_info
import requests
import os
from datetime import datetime

# ✅ API 端點
OVERTIME_API_URL = "https://linebot-on-render.onrender.com/api/overtime"
DOCTOR_SHEET_URL = "https://docs.google.com/spreadsheets/d/1fHf5XlbvLMd6ytAh_t8Bsi5ghToiQHZy1NlVfEG7VIo/edit"

# ✅ 轉換成民國日期格式
def to_roc_date(iso_date):
    y, m, d = map(int, iso_date.split("-"))
    return f"{y - 1911}年{m:02d}月{d:02d}日"

# ✅ 主處理邏輯
def handle_overtime(event, user_id, text, line_bot_api):
    session = get_session(user_id)
    step = session.get("step")
    data = session.get("data", {})

    # ✅ 進入流程
    if text == "加班申請":
        set_session(user_id, {"step": 1, "data": {}})
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請輸入加班日期（格式：YYYY-MM-DD）"))
        return True

    # ✅ Postback 處理
    if isinstance(event, PostbackEvent):
        if event.postback.data == "confirm_overtime":
            return submit_overtime(user_id, line_bot_api, event.reply_token)
        elif event.postback.data == "cancel_overtime":
            clear_session(user_id)
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="❌ 已取消加班申請"))
            return True

    # ✅ Step 1：輸入加班日期
    if step == 1:
        data["date"] = text
        set_session(user_id, {"step": 2, "data": data})
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請輸入加班時間（格式：HH:MM-HH:MM）"))
        return True

    # ✅ Step 2：輸入加班時間
    if step == 2:
        data["time"] = text
        set_session(user_id, {"step": 3, "data": data})
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請輸入加班事由"))
        return True

    # ✅ Step 3：輸入加班事由並確認
    if step == 3:
        data["reason"] = text

        # ✅ 查詢醫師姓名與科別
        name, dept = get_doctor_info(DOCTOR_SHEET_URL, user_id)
        data["name"] = name or "未知醫師"
        data["dept"] = dept or ""
        data["submitted_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # ✅ 民國格式日期
        roc_date = to_roc_date(data["date"])

        # ✅ 彈出確認畫面
        bubble = {
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "spacing": "md",
                "contents": [
                    {"type": "text", "text": "📝 請確認加班申請", "weight": "bold", "size": "lg"},
                    {"type": "separator"},
                    {"type": "box", "layout": "vertical", "margin": "md", "spacing": "sm", "contents": [
                        {"type": "text", "text": f"醫師：{data['name']}"},
                        {"type": "text", "text": f"科別：{data['dept']}"},
                        {"type": "text", "text": f"日期：{roc_date}"},
                        {"type": "text", "text": f"時間：{data['time']}"},
                        {"type": "text", "text": f"事由：{data['reason']}"}
                    ]}
                ]
            },
            "footer": {
                "type": "box",
                "layout": "horizontal",
                "spacing": "md",
                "contents": [
                    {
                        "type": "button",
                        "style": "primary",
                        "color": "#34c759",
                        "action": {"type": "postback", "label": "✅ 確認送出", "data": "confirm_overtime"}
                    },
                    {
                        "type": "button",
                        "style": "primary",
                        "color": "#ff3b30",
                        "action": {"type": "postback", "label": "❌ 取消", "data": "cancel_overtime"}
                    }
                ]
            }
        }

        set_session(user_id, {"step": 4, "data": data})
        line_bot_api.reply_message(event.reply_token, FlexSendMessage(alt_text="請確認加班申請", contents=bubble))
        return True

    return False

# ✅ Postback 確認送出
def submit_overtime(user_id, line_bot_api, reply_token):
    session = get_session(user_id)
    data = session.get("data", {})
    try:
        response = requests.post(OVERTIME_API_URL, json=data)
        result = response.json()
        if response.status_code == 200:
            msg = "✅ 加班申請已送出！"
        else:
            msg = f"❌ 送出失敗：{result}"
    except Exception as e:
        msg = f"❌ 發生錯誤：{e}"

    clear_session(user_id)
    line_bot_api.reply_message(reply_token, TextSendMessage(text=msg))
    return True
