
# app.py 最新整合版（含 LINE Bot 主選單、調診流程、檔案上傳、Google Sheets 與 Word 串接）

from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, FlexSendMessage
import os, json, requests, tempfile, datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

app = Flask(__name__)

# ✅ LINE BOT 設定
LINE_CHANNEL_ACCESS_TOKEN = 'LINE_CHANNEL_ACCESS_TOKEN'
LINE_CHANNEL_SECRET = 'LINE_CHANNEL_SECRET'
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# ✅ Google Drive Service Account
SERVICE_ACCOUNT_INFO = json.loads(os.environ["GOOGLE_CREDENTIALS"])
SCOPES = ["https://www.googleapis.com/auth/drive.file"]
credentials = service_account.Credentials.from_service_account_info(SERVICE_ACCOUNT_INFO, scopes=SCOPES)
drive_service = build("drive", "v3", credentials=credentials)

# ✅ 暫存使用者對話狀態
user_sessions = {}

# ✅ Flex 主選單（省略內容...）
main_menu = {...}
clinic_menu = {...}
other_menu = {...}

@app.route("/", methods=["GET"])
def index():
    return "LINE Bot is running"

@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers["X-Line-Signature"]
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"

# ✅ 檔案上傳到 Google Drive
def upload_to_drive(file_path, file_name):
    folder_id = "14LThiRWDO8zW7C0qrtobAVPrO_sAQtCW"
    file_metadata = {'name': file_name, 'parents': [folder_id]}
    media = MediaFileUpload(file_path, resumable=True)
    uploaded = drive_service.files().create(body=file_metadata, media_body=media, fields="id").execute()
    return uploaded.get("id")

# ✅ 處理訊息
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    text = event.message.text.strip()

    if text in ["主選單", "選單"]:
        line_bot_api.reply_message(event.reply_token, FlexSendMessage("主選單", main_menu))
    elif text == "門診調整服務":
        line_bot_api.reply_message(event.reply_token, FlexSendMessage("門診調整選單", clinic_menu))
    elif text == "其他表單服務":
        line_bot_api.reply_message(event.reply_token, FlexSendMessage("其他表單服務", other_menu))
    elif text == "我要上傳檔案":
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請直接傳送檔案，我會幫您儲存至雲端硬碟。"))
    elif text in ["我要調診", "我要休診", "我要代診", "我要加診"]:
        user_sessions[user_id] = {"step": 1, "type": text}
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請問原門診是哪一天？（例如：5/6 上午診）"))
    elif user_id in user_sessions:
        session = user_sessions[user_id]
        if session["step"] == 1:
            session["original_date"] = text
            session["step"] = 2
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請問您希望處理方式為？"))
        elif session["step"] == 2:
            session["new_date"] = text
            session["step"] = 3
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請問原因？"))
        elif session["step"] == 3:
            session["reason"] = text
            webhook_url = "https://script.google.com/macros/s/AKfycbwgmpLgjrhwquI54fpK-dIA0z0TxHLEfO2KmaX-meqE7ENNUHmB_ec9GC-7MNHNl1eJ/exec"
            data_to_send = {
                "user_id": user_id,
                "request_type": session["type"],
                "original_date": session["original_date"],
                "new_date": session["new_date"],
                "reason": session["reason"]
            }
            requests.post(webhook_url, json=data_to_send)
            result = f"✅ 已收到您的申請：\n申請類型：{session['type']}\n原門診：{session['original_date']}\n處理方式：{session['new_date']}\n原因：{session['reason']}"
            del user_sessions[user_id]
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=result))

# ✅ 接收檔案訊息
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
