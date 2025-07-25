# handlers/overtime_handler.py
import requests
from linebot.models import TextSendMessage, FlexSendMessage
from utils.session_manager import get_session, set_session, clear_session

API_URL = "https://linebot-on-render.onrender.com/api/overtime"  # ✅ 你的 API URL

def handle_overtime(event, user_id, text, line_bot_api):
    session = get_session(user_id)

    # ✅ 啟動流程
    if text == "加班申請" and not session:
        set_session(user_id, {"step": 1})
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="請輸入加班日期（格式：YYYY-MM-DD）")
        )
        return True

    # ✅ 如果不是加班流程，檢查是否按下 Flex 按鈕
    if text.startswith("確認送出加班申請") and session:
        return _confirm_overtime(event, user_id, line_bot_api)

    if text == "取消加班申請":
        clear_session(user_id)
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="❌ 已取消加班申請")
        )
        return True

    # ✅ 如果不是流程就 return False
    if not session:
        return False

    step = session.get("step")

    if step == 1:
        session["date"] = text
        session["step"] = 2
        set_session(user_id, session)
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="請輸入加班時間（格式：HH:MM-HH:MM）")
        )
        return True

    if step == 2:
        session["time"] = text
        session["step"] = 3
        set_session(user_id, session)
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="請輸入加班事由")
        )
        return True

    if step == 3:
        session["reason"] = text
        session["name"] = "未知醫師"  # ✅ 可以改成 Google Sheets 對應名稱
        session["step"] = "confirm"
        set_session(user_id, session)

        # ✅ 顯示 Flex 確認卡片
        flex = {
            "type": "bubble",
            "size": "mega",
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {"type": "text", "text": "📋 請確認加班申請", "weight": "bold", "size": "lg", "margin": "md"},
                    {"type": "separator", "margin": "md"},
                    {"type": "box", "layout": "vertical", "margin": "lg", "contents": [
                        {"type": "text", "text": f"日期：{session['date']}", "size": "md"},
                        {"type": "text", "text": f"時間：{session['time']}", "size": "md"},
                        {"type": "text", "text": f"事由：{session['reason']}", "size": "md"}
                    ]},
                    {"type": "separator", "margin": "lg"},
                    {"type": "box", "layout": "horizontal", "spacing": "md", "margin": "lg", "contents": [
                        {"type": "button", "style": "primary", "color": "#4CAF50",
                         "action": {"type": "message", "label": "✅ 確認送出", "text": "確認送出加班申請"}},
                        {"type": "button", "style": "secondary", "color": "#FF5252",
                         "action": {"type": "message", "label": "❌ 取消", "text": "取消加班申請"}}
                    ]}
                ]
            }
        }

        line_bot_api.reply_message(
            event.reply_token,
            FlexSendMessage(alt_text="確認加班申請", contents=flex)
        )
        return True

    return False


def _confirm_overtime(event, user_id, line_bot_api):
    session = get_session(user_id)
    if not session:
        return False

    try:
        res = requests.post(API_URL, json=session)
        if res.status_code == 200:
            msg = "✅ 加班申請已送出"
        else:
            msg = f"❌ 送出失敗：{res.text}"
    except Exception as e:
        msg = f"❌ 系統錯誤：{str(e)}"

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=msg)
    )
    clear_session(user_id)
    return True
