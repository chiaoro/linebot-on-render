
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, FlexSendMessage
import requests
import os, json, datetime, tempfile

app = Flask(__name__)

# LINE Bot 憑證
line_bot_api = LineBotApi('P/mPYhb4OFQiFRUQAltm0u520BesCQ6q38lv6krt/muIqyfCr3LH3XTdQEo9TyMyC9XnieVKrQPPUSS1Qp9Eeb6orbDYFO7r4byA52aC2OvI4xnu4nnR9J6FWds+r28kFNsR1VNdmjwa/k2MgIBysgdB04t89/1O/w1cDnyilFU=')
handler = WebhookHandler('adba7944fb5d5f596cad271add96b177')
user_sessions = {}

# Google Drive 設定
SERVICE_ACCOUNT_INFO = json.loads(os.environ['GOOGLE_CREDENTIALS'])
SCOPES = ['https://www.googleapis.com/auth/drive.file']
credentials = service_account.Credentials.from_service_account_info(SERVICE_ACCOUNT_INFO, scopes=SCOPES)
drive_service = build('drive', 'v3', credentials=credentials)

def upload_to_drive(file_path, file_name):
    folder_id = '你的 Google Drive 資料夾 ID'
    file_metadata = {'name': file_name, 'parents': [folder_id]}
    media = MediaFileUpload(file_path, resumable=True)
    uploaded = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    return uploaded.get('id')

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@app.route("/", methods=["GET"])
def index():
    return "LINE Bot is running!"

@handler.add(MessageEvent)
def handle_all_message(event):
    user_id = event.source.user_id
    message = event.message

    if isinstance(message, TextMessage):
        text = message.text.strip()
        if text == "我要調診" or text == "我要休診" or text == "我要代診" or text == "我要加診":
            user_sessions[user_id] = {"step": 1, "type": text}
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請問原本門診是哪一天（例如：5/6 上午診）？"))
            return

        if text in ["選單", "主選單"]:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="📌 請選擇服務：門診調整、支援醫師、新進醫師、其他表單"))
            return

        if user_id in user_sessions:
            session = user_sessions[user_id]
            step = session["step"]
            if step == 1:
                session["original_date"] = text
                session["step"] = 2
                ask = "請問您要調整到哪一天？" if session["type"] == "我要調診" else "請問您希望如何處理？"
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text=ask))
            elif step == 2:
                session["new_date"] = text
                session["step"] = 3
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請問原因是什麼？"))
            elif step == 3:
                session["reason"] = text
                webhook_url = "你的 Webhook URL"
                requests.post(webhook_url, json={
                    "user_id": user_id,
                    "request_type": session["type"],
                    "original_date": session["original_date"],
                    "new_date": session["new_date"],
                    "reason": session["reason"]
                })
                line_bot_api.reply_message(event.reply_token, TextSendMessage(
                    text=f"✅ 已收到申請：\n{session['type']}\n原門診：{session['original_date']}\n處理方式：{session['new_date']}\n原因：{session['reason']}"))
                del user_sessions[user_id]
            return

        if text == "我要上傳檔案":
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="📎 請直接傳送檔案，我會幫您儲存至雲端硬碟。"))
            return

        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請點選『選單』開始操作。"))

    elif hasattr(message, 'file_name'):
        ext = message.file_name.split('.')[-1]
        file_name = f"上傳檔案_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.{ext}"
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
