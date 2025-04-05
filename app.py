
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

import os

app = Flask(__name__)

line_bot_api = LineBotApi(os.environ.get("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.environ.get("LINE_CHANNEL_SECRET"))

user_sessions = {}

@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers["X-Line-Signature"]
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    text = event.message.text.strip()

    if text == "我要調診":
        user_sessions[user_id] = {"step": 1, "type": text}
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請問原本門診是哪一天？"))
        return

    if user_id in user_sessions:
        session = user_sessions[user_id]
        step = session.get("step", 0)

        if step == 1:
            session["original_date"] = text
            session["step"] = 2
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請問您要調整到哪一天？"))
        elif step == 2:
            session["new_date_or_plan"] = text
            session["step"] = 3
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請問原因是什麼？"))
        elif step == 3:
            session["reason"] = text
            session["step"] = 4

            result = f"""📋 新申請：
申請類型：{session['type']}
原門診：{session['original_date']}
處理方式：{session['new_date_or_plan']}
原因：{session['reason']}"""
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=result))
            del user_sessions[user_id]

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
