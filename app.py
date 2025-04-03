
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, FlexSendMessage
import requests

app = Flask(__name__)

# 請填入你的 Channel Access Token 和 Secret
line_bot_api = LineBotApi('P/mPYhb4OFQiFRUQAltm0u520BesCQ6q38lv6krt/muIqyfCr3LH3XTdQEo9TyMyC9XnieVKrQPPUSS1Qp9Eeb6orbDYFO7r4byA52aC2OvI4xnu4nnR9J6FWds+r28kFNsR1VNdmjwa/k2MgIBysgdB04t89/1O/w1cDnyilFU=')
handler = WebhookHandler('adba7944fb5d5f596cad271add96b177')

# 暫存使用者對話進度
user_sessions = {}

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    text = event.message.text.strip()

    if text in ["我要調診", "我要休診", "我要代診", "我要加診"]:
        user_sessions[user_id] = {"step": 1, "type": text}
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請問原本門診是哪一天（例如：5/6 早診）？"))
        return

    if user_id in user_sessions:
        session = user_sessions[user_id]
        step = session["step"]
        req_type = session["type"]

        if step == 1:
            session["original_date"] = text
            session["step"] = 2
            followup = "請問您要調整到哪一天（例如：5/13 早診）？" if req_type == "我要調診" else "請問您希望如何處理？（例如：整天休診、由張醫師代診、加開下午診）"
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=followup))
        elif step == 2:
            session["new_date_or_plan"] = text
            session["step"] = 3
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請問原因是什麼？"))
        elif step == 3:
            session["reason"] = text

            # 傳送資料到 Google Apps Script
            data_to_send = {
                "user_id": user_id,
                "request_type": req_type,
                "original_date": session["original_date"],
                "new_date_or_plan": session["new_date_or_plan"],
                "reason": session["reason"]
            }

            webhook_url = "https://script.google.com/macros/s/AKfycbwgmpLgjrhwquI54fpK-dIA0z0TxHLEfO2KmaX-meqE7ENNUHmB_ec9GC-7MNHNl1eJ/exec"
            requests.post(webhook_url, json=data_to_send)

            result = f"""✅ 已收到您的申請：
申請類型：{req_type}
原門診：{session['original_date']}
處理方式：{session['new_date_or_plan']}
原因：{session['reason']}"""

            del user_sessions[user_id]
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=result))
        return

    if text == "選單" or text == "menu":
        flex_message = FlexSendMessage(
            alt_text="醫師服務選單",
            contents={
                "type": "bubble",
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "text",
                            "text": "請選擇您要進行的服務項目：",
                            "weight": "bold",
                            "size": "lg",
                            "margin": "md"
                        },
                        {
                            "type": "button",
                            "action": {
                                "type": "message",
                                "label": "我要調診",
                                "text": "我要調診"
                            },
                            "style": "primary",
                            "margin": "md"
                        },
                        {
                            "type": "button",
                            "action": {
                                "type": "message",
                                "label": "我要休診",
                                "text": "我要休診"
                            },
                            "style": "primary",
                            "margin": "md"
                        },
                        {
                            "type": "button",
                            "action": {
                                "type": "message",
                                "label": "我要代診",
                                "text": "我要代診"
                            },
                            "style": "primary",
                            "margin": "md"
                        },
                        {
                            "type": "button",
                            "action": {
                                "type": "message",
                                "label": "我要加診",
                                "text": "我要加診"
                            },
                            "style": "primary",
                            "margin": "md"
                        }
                    ]
                }
            }
        )
        line_bot_api.reply_message(event.reply_token, flex_message)
        return

    line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請點選『選單』來開始操作。"))

import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Render 會提供環境變數 PORT
    app.run(host="0.0.0.0", port=port)
