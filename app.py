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

# ✅ LINE Bot 憑證
line_bot_api = LineBotApi(os.environ.get("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.environ.get("LINE_CHANNEL_SECRET"))


# ✅ 暫存對話流程
user_sessions = {}

# ✅ Google Drive 設定
SERVICE_ACCOUNT_INFO = json.loads(os.environ.get("GOOGLE_CREDENTIALS"))
SCOPES = ['https://www.googleapis.com/auth/drive.file']
credentials = service_account.Credentials.from_service_account_info(SERVICE_ACCOUNT_INFO, scopes=SCOPES)
drive_service = build('drive', 'v3', credentials=credentials)

# ✅ Google API Target
SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID")
TEMPLATE_DOC_ID = os.environ.get("TEMPLATE_DOC_ID")
TARGET_FOLDER_ID = os.environ.get("TARGET_FOLDER_ID")

# ✅ 主選單 Flex Message
main_menu = {
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

# ✅ 回傳檔案上傳到 Google Drive
def upload_to_drive(file_path, file_name):
    file_metadata = {'name': file_name, 'parents': [TARGET_FOLDER_ID]}
    media = MediaFileUpload(file_path, resumable=True)
    uploaded = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    return uploaded.get('id')

@app.route("/", methods=["GET"])
def index():
    return "LINE Bot is running!"

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
def handle_text(event):
    user_id = event.source.user_id
    text = event.message.text.strip()

    if text in ["選單", "主選單"]:
        line_bot_api.reply_message(event.reply_token, FlexSendMessage("主選單", main_menu))
        return

    if text in ["我要調診", "我要休診", "我要代診", "我要加診"]:
        user_sessions[user_id] = {"step": 1, "type": text}
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請問原本門診是哪一天（例如：5/6 上午診）？"))
        return

    if user_id in user_sessions:
        session = user_sessions[user_id]
        if session["step"] == 1:
            session["original_date"] = text
            session["step"] = 2
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請問您希望如何處理？"))
        elif session["step"] == 2:
            session["new_date"] = text
            session["step"] = 3
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請問原因是什麼？"))
        elif session["step"] == 3:
            session["reason"] = text
            data = {
                "user_id": user_id,
                "request_type": session["type"],
                "original_date": session["original_date"],
                "new_date": session["new_date"],
                "reason": session["reason"]
            }
            webhook_url = "https://script.google.com/macros/s/AKfycbwgmpLgjrhwquI54fpK-dIA0z0TxHLEfO2KmaX-meqE7ENNUHmB_ec9GC-7MNHNl1eJ/exec"
            requests.post(webhook_url, json=data)
            reply = f"""✅ 已收到您的申請：
申請類型：{session['type']}
原門診：{session['original_date']}
處理方式：{session['new_date']}
原因：{session['reason']}"""
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
            del user_sessions[user_id]
        return

    if text == "我要上傳檔案":
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="📎 請直接傳送檔案，我會幫您儲存至雲端硬碟。"))
        return

@handler.add(MessageEvent)
def handle_file(event):
    message = event.message
    if hasattr(message, 'file_name'):
        ext = message.file_name.split('.')[-1]
    else:
        ext = 'bin'
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
