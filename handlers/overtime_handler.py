# handlers/overtime_handler.py
from linebot.models import TextSendMessage
from utils.session_manager import get_session, set_session, clear_session
import requests

API_URL = "https://你的網址.onrender.com/api/overtime"  # 部署後更新

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

    # ✅ 如果不是加班流程，跳過
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
        session["name"] = "醫師姓名"  # TODO：未來從 LINE Profile 或前面收集

        # ✅ 呼叫後端 API
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

    return False
