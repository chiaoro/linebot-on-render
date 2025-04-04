from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, FlexSendMessage
)
import requests, os, json, tempfile, datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

app = Flask(__name__)

# === ✅ LINE BOT 憑證（Render 平台以環境變數儲存） ===
line_bot_api = LineBotApi(os.environ.get("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.environ.get("LINE_CHANNEL_SECRET"))

# === ✅ Google Drive API 驗證 ===
SERVICE_ACCOUNT_INFO = json.loads(os.environ.get("GOOGLE_CREDENTIALS"))
SCOPES = ['https://www.googleapis.com/auth/drive.file']
credentials = service_account.Credentials.from_service_account_info(SERVICE_ACCOUNT_INFO, scopes=SCOPES)
drive_service = build('drive', 'v3', credentials=credentials)

# === ✅ 全域變數與 Flex 主選單 ===
user_sessions = {}

main_menu = FlexSendMessage(
    alt_text="主選單",
    contents={
        "type": "bubble",
        "body": {
            "type": "box", "layout": "vertical", "contents": [
                {"type": "text", "text": "請選擇服務類別", "weight": "bold", "size": "lg"},
                {"type": "button", "action": {"type": "message", "label": "門診調整服務", "text": "門診調整服務"}, "style": "primary", "margin": "md"},
                {"type": "button", "action": {"type": "message", "label": "支援醫師服務", "text": "支援醫師服務"}, "style": "primary", "margin": "md"},
                {"type": "button", "action": {"type": "message", "label": "新進醫師服務", "text": "新進醫師服務"}, "style": "primary", "margin": "md"},
                {"type": "button", "action": {"type": "message", "label": "其他表單服務", "text": "其他表單服務"}, "style": "primary", "margin": "md"},
            ]
        }
    }
)

clinic_menu = FlexSendMessage(
    alt_text="門診調整服務",
    contents={
        "type": "bubble",
        "body": {
            "type": "box", "layout": "vertical", "contents": [
                {"type": "text", "text": "門診調整選單", "weight": "bold", "size": "lg"},
                {"type": "button", "action": {"type": "message", "label": "我要調診", "text": "我要調診"}, "style": "primary", "margin": "md"},
                {"type": "button", "action": {"type": "message", "label": "我要代診", "text": "我要代診"}, "style": "primary", "margin": "md"},
                {"type": "button", "action": {"type": "message", "label": "我要休診", "text": "我要休診"}, "style": "primary", "margin": "md"},
                {"type": "button", "action": {"type": "message", "label": "我要加診", "text": "我要加診"}, "style": "primary", "margin": "md"},
            ]
        }
    }
)

other_menu = FlexSendMessage(
    alt_text="其他表單服務",
    contents={
        "type": "bubble",
        "body": {
            "type": "box", "layout": "vertical", "contents": [
                {"type": "text", "text": "其他表單服務", "weight": "bold", "size": "lg"},
                {"type": "button", "action": {"type": "message", "label": "Temp 傳檔", "text": "我要上傳檔案"}, "style": "secondary", "margin": "md"},
            ]
        }
    }
)

# === ✅ Webhook 接收 ===
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"

# === ✅ 上傳檔案處理 ===
def upload_to_drive(file_path, file_name):
    folder_id = "14LThiRWDO8zW7C0qrtobAVPrO_sAQtCW"  # 你的 Google Drive 資料夾 ID
    file_metadata = {'name': file_name, 'parents': [folder_id]}
    media = MediaFileUpload(file_path, resumable=True)
    uploaded = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    return uploaded.get('id')

# === ✅ 處理 LINE 訊息 ===
@handler.add(MessageEvent, message=TextMessage)
def handle_text(event):
    user_id = event.source.user_id
    text = event.message.text.strip()

    if text in ["主選單", "選單"]:
        line_bot_api.reply_message(event.reply_token, main_menu)
    elif text == "門診調整服務":
        line_bot_api.reply_message(event.reply_token, clinic_menu)
    elif text == "其他表單服務":
        line_bot_api.reply_message(event.reply_token, other_menu)
    elif text == "我要上傳檔案":
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="📎 請傳送檔案，我會上傳至雲端。"))
    elif text in ["我要調診", "我要代診", "我要休診", "我要加診"]:
        user_sessions[user_id] = {"step": 1, "type": text}
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請問原門診日期？（例如：5/10 上午診）"))
    elif user_id in user_sessions:
        session = user_sessions[user_id]
        if session["step"] == 1:
            session["original_date"] = text
            session["step"] = 2
            next_q = "請問要調整到哪天？" if session["type"] == "我要調診" else "請問您希望如何處理？"
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=next_q))
        elif session["step"] == 2:
            session["new_date"] = text
            session["step"] = 3
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請輸入原因"))
        elif session["step"] == 3:
            session["reason"] = text
            requests.post("https://script.google.com/macros/s/AKfycbwgmpLgjrhwquI54fpK-dIA0z0TxHLEfO2KmaX-meqE7ENNUHmB_ec9GC-7MNHNl1eJ/exec", json={
                "user_id": user_id,
                "request_type": session["type"],
                "original_date": session["original_date"],
                "new_date": session["new_date"],
                "reason": session["reason"]
            })
            summary = f"""✅ 已收到您的申請：
申請類型：{session['type']}
原門診：{session['original_date']}
處理方式：{session['new_date']}
原因：{session['reason']}"""
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=summary))
            del user_sessions[user_id]
    else:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請點選『選單』開始操作"))

# === ✅ 傳檔事件（非文字訊息） ===
@handler.add(MessageEvent)
def handle_file(event):
    if hasattr(event.message, "file_name"):
        file_name = event.message.file_name
    else:
        ext = "bin"
        file_name = f"上傳檔案_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.{ext}"

    message_content = line_bot_api.get_message_content(event.message.id)
    with tempfile.NamedTemporaryFile(delete=False) as tf:
        for chunk in message_content.iter_content():
            tf.write(chunk)
        temp_path = tf.name

    upload_to_drive(temp_path, file_name)
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text="✅ 檔案已成功上傳至雲端"))

# === ✅ 顯示首頁 ===
@app.route("/")
def index():
    return "LINE Bot 正在運作中..."

# === ✅ 運行 Flask App ===
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
