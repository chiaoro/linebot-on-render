
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, FlexSendMessage
)
import requests
import os

app = Flask(__name__)

line_bot_api = LineBotApi(os.environ.get("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.environ.get("LINE_CHANNEL_SECRET"))
admin_user_id = os.environ.get("LINE_ADMIN_USER_ID")

# 儲存使用者三步驟資料
user_sessions = {}

# Flex Bubble 主選單
main_menu = FlexSendMessage(
    alt_text="主選單",
    contents={
        "type": "bubble",
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "contents": [
                {"type": "text", "text": "請選擇服務類別", "weight": "bold", "size": "lg"},
                *[
                    {
                        "type": "button",
                        "action": {"type": "message", "label": label, "text": label},
                        "style": "primary"
                    }
                    for label in ["門診調整服務", "支援醫師服務", "新進醫師服務", "其他表單服務"]
                ]
            ]
        }
    }
)

@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers["X-Line-Signature"]
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except:
        abort(400)
    return "OK"

@app.route("/", methods=["GET"])
def index():
    return "Line Bot is running!"

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    text = event.message.text.strip()

    if text in ["主選單", "選單"]:
        line_bot_api.reply_message(event.reply_token, main_menu)
        return

    if text in ["我要調診", "我要代診", "我要休診", "我要加診"]:
        user_sessions[user_id] = {"step": 1, "type": text}
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請問原本門診是哪一天（例如：5/6 上午診）？"))
        return

    if user_id in user_sessions:
        session = user_sessions[user_id]
        step = session["step"]

        if step == 1:
            session["original_date"] = text
            session["step"] = 2
            prompt = "請問您要調整到哪一天？" if session["type"] == "我要調診" else "請問您希望如何處理？"
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=prompt))
        elif step == 2:
            session["new_date_or_plan"] = text
            session["step"] = 3
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請問原因是什麼？"))
        elif step == 3:
            session["reason"] = text
            summary = f"✅ 已收到您的申請：\n申請類型：{session['type']}\n原門診：{session['original_date']}\n處理方式：{session['new_date_or_plan']}\n原因：{session['reason']}"
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=summary))

            # 推播到管理者
            notify_admin(user_id, session)
            del user_sessions[user_id]

def notify_admin(user_id, session):
    message = f"📩 收到申請：\n{session['type']}\n原門診：{session['original_date']}\n新門診：{session['new_date_or_plan']}\n原因：{session['reason']}"
    line_bot_api.push_message(admin_user_id, TextSendMessage(text=message))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
