from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, FlexSendMessage
)
import requests
import os

app = Flask(__name__)

# ✅ LINE Bot 憑證
line_bot_api = LineBotApi('P/mPYhb4OFQiFRUQAltm0u520BesCQ6q38lv6krt/muIqyfCr3LH3XTdQEo9TyMyC9XnieVKrQPPUSS1Qp9Eeb6orbDYFO7r4byA52aC2OvI4xnu4nnR9J6FWds+r28kFNsR1VNdmjwa/k2MgIBysgdB04t89/1O/w1cDnyilFU=')
handler = WebhookHandler('adba7944fb5d5f596cad271add96b177')

# ✅ 暫存對話流程
user_sessions = {}

# ✅ 主選單 Flex Message
main_menu = FlexSendMessage(
    alt_text="主選單",
    contents={
        "type": "bubble",
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {"type": "text", "text": "請選擇服務類別", "weight": "bold", "size": "lg"},
                {
                    "type": "button",
                    "action": {"type": "message", "label": "門診調整服務", "text": "門診調整服務"},
                    "style": "primary", "margin": "md"
                },
                {
                    "type": "button",
                    "action": {"type": "message", "label": "支援醫師服務", "text": "支援醫師服務"},
                    "style": "primary", "margin": "md"
                },
                {
                    "type": "button",
                    "action": {"type": "message", "label": "新進醫師服務", "text": "新進醫師服務"},
                    "style": "primary", "margin": "md"
                },
                {
                    "type": "button",
                    "action": {"type": "message", "label": "其他表單服務", "text": "其他表單服務"},
                    "style": "primary", "margin": "md"
                }
            ]
        }
    }
)

# ✅ 子選單
clinic_menu = FlexSendMessage(
    alt_text="門診調整服務",
    contents={
        "type": "bubble",
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {"type": "text", "text": "門診調整選單", "weight": "bold", "size": "lg"},
                {
                    "type": "button", "action": {"type": "message", "label": "我要調診", "text": "我要調診"},
                    "style": "primary", "margin": "md"
                },
                {
                    "type": "button", "action": {"type": "message", "label": "我要代診", "text": "我要代診"},
                    "style": "primary", "margin": "md"
                },
                {
                    "type": "button", "action": {"type": "message", "label": "我要休診", "text": "我要休診"},
                    "style": "primary", "margin": "md"
                },
                {
                    "type": "button", "action": {"type": "message", "label": "我要加診", "text": "我要加診"},
                    "style": "primary", "margin": "md"
                }
            ]
        }
    }
)

newcomer_menu = FlexSendMessage(
    alt_text="新進醫師服務",
    contents={
        "type": "bubble",
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {"type": "text", "text": "新進醫師服務", "weight": "bold", "size": "lg"},
                {
                    "type": "button",
                    "action": {
                        "type": "uri",
                        "label": "必填資料",
                        "uri": "https://docs.google.com/forms/d/e/1FAIpQLScUn1Bm83wZ7SSTYCl8fj7z3b_sq7tscrZiXSt_AXOHf0SKPw/viewform"
                    },
                    "style": "secondary", "margin": "md"
                },
                {
                    "type": "button",
                    "action": {
                        "type": "uri",
                        "label": "新進須知",
                        "uri": "https://docs.google.com/forms/d/e/1FAIpQLSfH7139NRH2SbV8BjRBioXHtD_6KLMYtfmktJxEBxUc7OW3Kg/viewform"
                    },
                    "style": "secondary", "margin": "md"
                }
            ]
        }
    }
)

support_menu = FlexSendMessage(
    alt_text="支援醫師服務",
    contents={
        "type": "bubble",
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {"type": "text", "text": "支援醫師服務", "weight": "bold", "size": "lg"},
                {
                    "type": "button",
                    "action": {
                        "type": "uri",
                        "label": "必填資料",
                        "uri": "https://docs.google.com/forms/d/e/1FAIpQLSe0uYZEF2-bBY14_nKlykFuV__CEeEeOaGVrQJiai9cVoZWLQ/viewform"
                    },
                    "style": "secondary", "margin": "md"
                }
            ]
        }
    }
)

other_menu = FlexSendMessage(
    alt_text="其他表單服務",
    contents={
        "type": "bubble",
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {"type": "text", "text": "其他表單服務", "weight": "bold", "size": "lg"},
                {
                    "type": "button",
                    "action": {"type": "message", "label": "Temp 傳檔", "text": "我要上傳檔案"},
                    "style": "secondary", "margin": "md"
                }
            ]
        }
    }
)

# ✅ Webhook 接收
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

# ✅ 頁面顯示
@app.route("/", methods=["GET"])
def index():
    return "LINE Bot is running!"

# ✅ 處理訊息與三步驟流程
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    text = event.message.text.strip()

    if text in ["選單", "主選單"]:
        line_bot_api.reply_message(event.reply_token, main_menu)
        return
    elif text == "門診調整服務":
        line_bot_api.reply_message(event.reply_token, clinic_menu)
        return
    elif text == "新進醫師服務":
        line_bot_api.reply_message(event.reply_token, newcomer_menu)
        return
    elif text == "支援醫師服務":
        line_bot_api.reply_message(event.reply_token, support_menu)
        return
    elif text == "其他表單服務":
        line_bot_api.reply_message(event.reply_token, other_menu)
        return
    elif text == "我要上傳檔案":
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="📎 請直接傳送檔案，我會幫您儲存至雲端硬碟。"))
        return

    if text in ["我要調診", "我要休診", "我要代診", "我要加診"]:
        user_sessions[user_id] = {"step": 1, "type": text}
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請問原本門診是哪一天（例如：5/6 上午診）？"))
        return

    if user_id in user_sessions:
        session = user_sessions[user_id]
        step = session["step"]
        req_type = session["type"]

        if step == 1:
            session["original_date"] = text
            session["step"] = 2
            next_question = "請問您要調整到哪一天？" if req_type == "我要調診" else "請問您希望如何處理？（例如：由張醫師代診）"
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=next_question))
        elif step == 2:
            session["new_date"] = text
            session["step"] = 3
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請問原因是什麼？"))
        elif step == 3:
            session["reason"] = text

            # 送出資料到 Google Apps Script
            webhook_url = "https://script.google.com/macros/s/AKfycbwgmpLgjrhwquI54fpK-dIA0z0TxHLEfO2KmaX-meqE7ENNUHmB_ec9GC-7MNHNl1eJ/exec"
            data_to_send = {
                "user_id": user_id,
                "request_type": session["type"],
                "original_date": session["original_date"],
                "new_date": session["new_date"],
                "reason": session["reason"]
            }
            requests.post(webhook_url, json=data_to_send)

            summary = f"""✅ 已收到您的申請：
申請類型：{session['type']}
原門診：{session['original_date']}
處理方式：{session['new_date']}
原因：{session['reason']}"""

            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=summary))
            del user_sessions[user_id]
        return

    line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請點選『選單』開始操作。"))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
