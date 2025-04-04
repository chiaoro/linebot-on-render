from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
    FlexSendMessage, FileMessage
)
import os, json, requests, tempfile, datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

app = Flask(__name__)

line_bot_api = LineBotApi('YOUR_CHANNEL_ACCESS_TOKEN')
handler = WebhookHandler('YOUR_CHANNEL_SECRET')

SERVICE_ACCOUNT_INFO = json.loads(os.environ['GOOGLE_CREDENTIALS'])
SCOPES = ['https://www.googleapis.com/auth/drive.file']
credentials = service_account.Credentials.from_service_account_info(SERVICE_ACCOUNT_INFO, scopes=SCOPES)
drive_service = build('drive', 'v3', credentials=credentials)

user_sessions = {}

def upload_to_drive(file_path, file_name):
    folder_id = '14LThiRWDO8zW7C0qrtobAVPrO_sAQtCW'
    file_metadata = {'name': file_name, 'parents': [folder_id]}
    media = MediaFileUpload(file_path, resumable=True)
    uploaded = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    return uploaded.get("id")

main_menu = {
    "type": "bubble",
    "body": {
        "type": "box", "layout": "vertical", "contents": [
            {"type": "text", "text": "請選擇服務類別", "weight": "bold", "size": "lg"},
            {"type": "button", "action": {"type": "message", "label": "門診調整服務", "text": "門診調整服務"}, "style": "primary"},
            {"type": "button", "action": {"type": "message", "label": "新進醫師服務", "text": "新進醫師服務"}, "style": "primary"},
            {"type": "button", "action": {"type": "message", "label": "支援醫師服務", "text": "支援醫師服務"}, "style": "primary"},
            {"type": "button", "action": {"type": "message", "label": "其他表單服務", "text": "其他表單服務"}, "style": "primary"},
        ]
    }
}

@app.route("/", methods=["GET"])
def index():
    return "LINE Bot is running"

@app.route("/callback", methods=["POST"])
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
    if text in ["主選單", "選單"]:
        line_bot_api.reply_message(event.reply_token, FlexSendMessage("主選單", main_menu))
        return
    elif text == "門診調整服務":
        options = "\n".join(["✅ 我要調診", "✅ 我要代診", "✅ 我要休診", "✅ 我要加診"])
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"請選擇服務：\n{options}"))
        return
    elif text == "新進醫師服務":
        msg = (
            "📋 新進醫師相關表單：\n"
            "✅ [必填資料](https://docs.google.com/forms/d/e/1FAIpQLScUn1Bm83wZ7SSTYCl8fj7z3b_sq7tscrZiXSt_AXOHf0SKPw/viewform)\n"
            "✅ [新進須知](https://docs.google.com/forms/d/e/1FAIpQLSfH7139NRH2SbV8BjRBioXHtD_6KLMYtfmktJxEBxUc7OW3Kg/viewform)"
        )
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=msg))
        return
    elif text == "支援醫師服務":
        msg = (
            "🆘 支援醫師表單：\n"
            "✅ [必填資料](https://docs.google.com/forms/d/e/1FAIpQLSe0uYZEF2-bBY14_nKlykFuV__CEeEeOaGVrQJiai9cVoZWLQ/viewform)"
        )
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=msg))
        return
    elif text == "其他表單服務":
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="📎 請直接傳送檔案，我會儲存至雲端。"))
        return

    if text in ["我要調診", "我要休診", "我要代診", "我要加診"]:
        user_sessions[user_id] = {"step": 1, "type": text}
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請問原門診是哪一天（例如：5/6 上午診）？"))
        return

    if user_id in user_sessions:
        session = user_sessions[user_id]
        if session["step"] == 1:
            session["original_date"] = text
            session["step"] = 2
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請問您希望如何處理？（例如：5/10 下午診）"))
        elif session["step"] == 2:
            session["new_date"] = text
            session["step"] = 3
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請問原因是什麼？"))
        elif session["step"] == 3:
            session["reason"] = text
            payload = {
                "user_id": user_id,
                "request_type": session["type"],
                "original_date": session["original_date"],
                "new_date": session["new_date"],
                "reason": session["reason"]
            }
            requests.post("https://script.google.com/macros/s/AKfycbwgmpLgjrhwquI54fpK-dIA0z0TxHLEfO2KmaX-meqE7ENNUHmB_ec9GC-7MNHNl1eJ/exec", json=payload)
            msg = f"✅ 已收到您的申請：\n類型：{session['type']}\n原門診：{session['original_date']}\n處理方式：{session['new_date']}\n原因：{session['reason']}"
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=msg))
            del user_sessions[user_id]

@handler.add(MessageEvent, message=FileMessage)
def handle_file(event):
    file_name = f"{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{event.message.file_name}"
    message_content = line_bot_api.get_message_content(event.message.id)
    with tempfile.NamedTemporaryFile(delete=False) as tf:
        for chunk in message_content.iter_content():
            tf.write(chunk)
        temp_path = tf.name
    upload_to_drive(temp_path, file_name)
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text="✅ 檔案已成功上傳至雲端"))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
