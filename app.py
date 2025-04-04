from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from linebot.exceptions import InvalidSignatureError
from linebot.models import (MessageEvent, TextMessage, TextSendMessage, FlexSendMessage)
import requests
import os, json, tempfile, datetime

app = Flask(__name__)

# LINE Bot credentials
line_bot_api = LineBotApi(os.environ['LINE_CHANNEL_ACCESS_TOKEN'])
handler = WebhookHandler(os.environ['LINE_CHANNEL_SECRET'])

# Google Drive Service Account
SERVICE_ACCOUNT_INFO = json.loads(os.environ['GOOGLE_CREDENTIALS'])
SCOPES = ['https://www.googleapis.com/auth/drive.file']
credentials = service_account.Credentials.from_service_account_info(SERVICE_ACCOUNT_INFO, scopes=SCOPES)
drive_service = build('drive', 'v3', credentials=credentials)

def upload_to_drive(file_path, file_name):
    folder_id = '14LThiRWDO8zW7C0qrtobAVPrO_sAQtCW'
    file_metadata = {
        'name': file_name,
        'parents': [folder_id]
    }
    media = MediaFileUpload(file_path, resumable=True)
    uploaded = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    return uploaded.get('id')

# Flex 主選單
main_menu = FlexSendMessage(
    alt_text="主選單",
    contents={
        "type": "bubble",
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {"type": "text", "text": "請選擇服務類別", "weight": "bold", "size": "lg"},
                {"type": "button", "action": {"type": "message", "label": "門診調整服務", "text": "門診調整服務"}, "style": "primary", "margin": "md"},
                {"type": "button", "action": {"type": "message", "label": "支援醫師服務", "text": "支援醫師服務"}, "style": "primary", "margin": "md"},
                {"type": "button", "action": {"type": "message", "label": "新進醫師服務", "text": "新進醫師服務"}, "style": "primary", "margin": "md"},
                {"type": "button", "action": {"type": "message", "label": "其他表單服務", "text": "其他表單服務"}, "style": "primary", "margin": "md"}
            ]
        }
    }
)

# 子選單們
clinic_menu = FlexSendMessage(
    alt_text="門診調整服務",
    contents={
        "type": "bubble",
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {"type": "text", "text": "門診調整選單", "weight": "bold", "size": "lg"},
                {"type": "button", "action": {"type": "message", "label": "我要調診", "text": "我要調診"}, "style": "primary", "margin": "md"},
                {"type": "button", "action": {"type": "message", "label": "我要代診", "text": "我要代診"}, "style": "primary", "margin": "md"},
                {"type": "button", "action": {"type": "message", "label": "我要休診", "text": "我要休診"}, "style": "primary", "margin": "md"},
                {"type": "button", "action": {"type": "message", "label": "我要加診", "text": "我要加診"}, "style": "primary", "margin": "md"}
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
                {"type": "button", "action": {"type": "uri", "label": "必填資料", "uri": "https://docs.google.com/forms/d/e/1FAIpQLScUn1Bm83wZ7SSTYCl8fj7z3b_sq7tscrZiXSt_AXOHf0SKPw/viewform"}, "style": "secondary", "margin": "md"},
                {"type": "button", "action": {"type": "uri", "label": "新進須知", "uri": "https://docs.google.com/forms/d/e/1FAIpQLSfH7139NRH2SbV8BjRBioXHtD_6KLMYtfmktJxEBxUc7OW3Kg/viewform"}, "style": "secondary", "margin": "md"}
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
                {"type": "button", "action": {"type": "uri", "label": "必填資料", "uri": "https://docs.google.com/forms/d/e/1FAIpQLSe0uYZEF2-bBY14_nKlykFuV__CEeEeOaGVrQJiai9cVoZWLQ/viewform"}, "style": "secondary", "margin": "md"}
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
                {"type": "button", "action": {"type": "message", "label": "Temp 傳檔", "text": "我要上傳檔案"}, "style": "secondary", "margin": "md"}
            ]
        }
    }
)

@app.route("/", methods=["GET"])
def index():
    return "LINE Bot is running!"

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
def handle_text(event):
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

@handler.add(MessageEvent)
def handle_file(event):
    message = event.message
    if hasattr(message, 'file_name') or hasattr(message, 'id'):
        ext = getattr(message, 'file_name', 'bin').split('.')[-1]
        file_name = f"LINE_上傳檔案_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.{ext}"

        message_content = line_bot_api.get_message_content(message.id)
        with tempfile.NamedTemporaryFile(delete=False) as tf:
            for chunk in message_content.iter_content():
                tf.write(chunk)
            temp_path = tf.name

        upload_to_drive(temp_path, file_name)

        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="✅ 檔案已成功上傳至雲端硬碟。"))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
