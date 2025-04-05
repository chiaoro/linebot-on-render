from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import *
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import tempfile, os, json, datetime, requests

app = Flask(__name__)

# ✅ LINE 憑證
line_bot_api = LineBotApi(os.environ['LINE_CHANNEL_ACCESS_TOKEN'])
handler = WebhookHandler(os.environ['LINE_CHANNEL_SECRET'])
ADMIN_USER_ID = os.environ['LINE_ADMIN_USER_ID']

# ✅ Google Drive 上傳初始化
SERVICE_ACCOUNT_INFO = json.loads(os.environ['GOOGLE_CREDENTIALS'])
SCOPES = ['https://www.googleapis.com/auth/drive.file']
credentials = service_account.Credentials.from_service_account_info(SERVICE_ACCOUNT_INFO, scopes=SCOPES)
drive_service = build('drive', 'v3', credentials=credentials)
UPLOAD_FOLDER_ID = '14LThiRWDO8zW7C0qrtobAVPrO_sAQtCW'

# ✅ 上傳檔案至 Google Drive
def upload_to_drive(file_path, file_name):
    file_metadata = {'name': file_name, 'parents': [UPLOAD_FOLDER_ID]}
    media = MediaFileUpload(file_path, resumable=True)
    uploaded = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    return uploaded.get('id')

# ✅ 使用者對話暫存
user_sessions = {}

# ✅ 主選單與 Flex 子選單
def get_main_menu():
    return FlexSendMessage("主選單", {
        "type": "bubble",
        "body": {
            "type": "box", "layout": "vertical", "contents": [
                {"type": "text", "text": "📋 請選擇服務類別", "weight": "bold", "size": "lg", "margin": "md"},
                *[
                    {
                        "type": "button",
                        "action": {"type": "message", "label": label, "text": label},
                        "style": "primary", "margin": "md"
                    } for label in ["門診調整服務", "支援醫師服務", "新進醫師服務", "其他表單服務"]
                ]
            ]
        }
    })

def get_submenu(title, buttons):
    return FlexSendMessage(title, {
        "type": "bubble",
        "body": {
            "type": "box", "layout": "vertical", "contents": [
                {"type": "text", "text": f"📂 {title}", "weight": "bold", "size": "lg", "margin": "md"},
                *buttons
            ]
        }
    })

clinic_buttons = [{"type": "button", "action": {"type": "message", "label": txt, "text": txt}, "style": "primary", "margin": "md"} for txt in ["我要調診", "我要休診", "我要代診", "我要加診"]]
support_buttons = [{"type": "button", "action": {"type": "uri", "label": "必填資料", "uri": "https://docs.google.com/forms/d/e/1FAIpQLSe0uYZEF2-bBY14_nKlykFuV__CEeEeOaGVrQJiai9cVoZWLQ/viewform"}, "style": "secondary", "margin": "md"}]
newcomer_buttons = [
    {"type": "button", "action": {"type": "uri", "label": "必填資料", "uri": "https://docs.google.com/forms/d/e/1FAIpQLScUn1Bm83wZ7SSTYCl8fj7z3b_sq7tscrZiXSt_AXOHf0SKPw/viewform"}, "style": "secondary", "margin": "md"},
    {"type": "button", "action": {"type": "uri", "label": "新進須知", "uri": "https://docs.google.com/forms/d/e/1FAIpQLSfH7139NRH2SbV8BjRBioXHtD_6KLMYtfmktJxEBxUc7OW3Kg/viewform"}, "style": "secondary", "margin": "md"}
]
other_buttons = [{"type": "button", "action": {"type": "message", "label": "Temp 傳檔", "text": "我要上傳檔案"}, "style": "secondary", "margin": "md"}]

@app.route("/", methods=["GET"])
def home():
    return "LINE Bot is running"

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

    if text == "主選單":
        line_bot_api.reply_message(event.reply_token, get_main_menu())
    elif text == "門診調整服務":
        line_bot_api.reply_message(event.reply_token, get_submenu("門診調整選單", clinic_buttons))
    elif text == "支援醫師服務":
        line_bot_api.reply_message(event.reply_token, get_submenu("支援醫師服務", support_buttons))
    elif text == "新進醫師服務":
        line_bot_api.reply_message(event.reply_token, get_submenu("新進醫師服務", newcomer_buttons))
    elif text == "其他表單服務":
        line_bot_api.reply_message(event.reply_token, get_submenu("其他表單服務", other_buttons))
    elif text == "我要上傳檔案":
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="📎 請直接傳送檔案，我會幫您儲存至雲端硬碟。"))
    elif text in ["我要調診", "我要休診", "我要代診", "我要加診"]:
        user_sessions[user_id] = {"step": 1, "type": text}
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請問原本門診是哪一天（例如：5/6 上午診）？"))
    elif user_id in user_sessions:
        session = user_sessions[user_id]
        if session["step"] == 1:
            session["original_date"] = text
            session["step"] = 2
            ask = "請問您要調整到哪一天？" if session["type"] == "我要調診" else "請問您希望如何處理？"
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=ask))
        elif session["step"] == 2:
            session["new_date"] = text
            session["step"] = 3
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請問原因是什麼？"))
        elif session["step"] == 3:
            session["reason"] = text
            webhook_url = "https://script.google.com/macros/s/AKfycbwgmpLgjrhwquI54fpK-dIA0z0TxHLEfO2KmaX-meqE7ENNUHmB_ec9GC-7MNHNl1eJ/exec"
            requests.post(webhook_url, json={
                "user_id": user_id,
                "request_type": session["type"],
                "original_date": session["original_date"],
                "new_date": session["new_date"],
                "reason": session["reason"]
            })
            line_bot_api.reply_message(
                event.reply_token, 
                TextSendMessage(text=f"""✅ 已收到您的申請：
申請類型：{session['type']}
原門診：{session['original_date']}
處理方式：{session['new_date']}
原因：{session['reason']}"
            ))
            del user_sessions[user_id]
    else:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請輸入『主選單』來開始操作。"))

@handler.add(MessageEvent, message=FileMessage)
def handle_file(event):
    message_content = line_bot_api.get_message_content(event.message.id)
    file_name = f"{event.message.file_name}"
    with tempfile.NamedTemporaryFile(delete=False) as tf:
        for chunk in message_content.iter_content():
            tf.write(chunk)
        temp_path = tf.name
    upload_to_drive(temp_path, file_name)
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text="✅ 檔案已成功上傳至雲端"))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
