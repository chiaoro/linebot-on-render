import os, json, tempfile, datetime
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, FileMessage, TextSendMessage, FlexSendMessage
)
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import requests

app = Flask(__name__)

# ====== LINE Bot 憑證與使用者設定 ======
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
LINE_ADMIN_USER_ID = os.getenv("LINE_ADMIN_USER_ID")
GAS_WEBHOOK_URL = os.getenv("GAS_WEBHOOK_URL")

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# ====== Google Drive Service Account 授權設定 ======
SERVICE_ACCOUNT_INFO = json.loads(os.environ['GOOGLE_CREDENTIALS'])
SCOPES = ['https://www.googleapis.com/auth/drive.file']
credentials = service_account.Credentials.from_service_account_info(SERVICE_ACCOUNT_INFO, scopes=SCOPES)
drive_service = build('drive', 'v3', credentials=credentials)
GOOGLE_DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID")

# ====== 使用者會話儲存區 ======
user_sessions = {}

# ====== Flex Bubble 主選單與子選單 ======
def get_main_menu():
    return {
        "type": "bubble",
        "body": {
            "type": "box", "layout": "vertical", "contents": [
                {"type": "text", "text": "請選擇服務類別", "weight": "bold", "size": "lg", "margin": "md"},
                *[{
                    "type": "button", "action": {"type": "message", "label": label, "text": label},
                    "style": "primary", "margin": "md"
                } for label in ["門診調整服務", "支援醫師服務", "新進醫師服務", "其他表單服務"]]
            ]
        }
    }

def get_sub_menu(title, options):
    return {
        "type": "bubble",
        "body": {
            "type": "box", "layout": "vertical", "contents": [
                {"type": "text", "text": title, "weight": "bold", "size": "lg", "margin": "md"},
                *[{
                    "type": "button",
                    "action": {
                        "type": "message" if "text" in opt else "uri",
                        "label": opt["label"],
                        "text": opt.get("text", ""),
                        "uri": opt.get("uri", "")
                    },
                    "style": "secondary", "margin": "md"
                } for opt in options]
            ]
        }
    }

clinic_options = [{"label": label, "text": label} for label in ["我要調診", "我要代診", "我要休診", "我要加診"]]
support_options = [{"label": "必填資料", "uri": "https://docs.google.com/forms/d/e/1FAIpQLSe0uYZEF2-bBY14_nKlykFuV__CEeEeOaGVrQJiai9cVoZWLQ/viewform"}]
newcomer_options = [
    {"label": "必填資料", "uri": "https://docs.google.com/forms/d/e/1FAIpQLScUn1Bm83wZ7SSTYCl8fj7z3b_sq7tscrZiXSt_AXOHf0SKPw/viewform"},
    {"label": "新進須知", "uri": "https://docs.google.com/forms/d/e/1FAIpQLSfH7139NRH2SbV8BjRBioXHtD_6KLMYtfmktJxEBxUc7OW3Kg/viewform"}
]
other_options = [{"label": "Temp 傳檔", "text": "我要上傳檔案"}]

# ====== Webhook 接收 ======
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

# ====== 主訊息處理 ======
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    text = event.message.text.strip()

    if text in ["選單", "主選單"]:
        line_bot_api.reply_message(event.reply_token, FlexSendMessage("主選單", get_main_menu()))
        return
    elif text == "門診調整服務":
        line_bot_api.reply_message(event.reply_token, FlexSendMessage("門診調整服務", get_sub_menu("門診調整服務", clinic_options)))
        return
    elif text == "支援醫師服務":
        line_bot_api.reply_message(event.reply_token, FlexSendMessage("支援醫師服務", get_sub_menu("支援醫師服務", support_options)))
        return
    elif text == "新進醫師服務":
        line_bot_api.reply_message(event.reply_token, FlexSendMessage("新進醫師服務", get_sub_menu("新進醫師服務", newcomer_options)))
        return
    elif text == "其他表單服務":
        line_bot_api.reply_message(event.reply_token, FlexSendMessage("其他表單服務", get_sub_menu("其他表單服務", other_options)))
        return
    elif text == "我要上傳檔案":
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="📎 請直接傳送檔案，我會幫您儲存至雲端硬碟。"))
        return
    elif text in ["我要調診", "我要代診", "我要休診", "我要加診"]:
        user_sessions[user_id] = {"step": 1, "type": text}
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請問原本門診是哪一天（例如：5/6 上午診）？"))
        return

    # 三步驟流程進行中
    if user_id in user_sessions:
        session = user_sessions[user_id]
        if session["step"] == 1:
            session["original_date"] = text
            session["step"] = 2
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請問您要調整到哪一天？"))
        elif session["step"] == 2:
            session["new_date_or_plan"] = text
            session["step"] = 3
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請問原因是什麼？"))
        elif session["step"] == 3:
            session["reason"] = text
            payload = {
                "user_id": user_id,
                "request_type": session["type"],
                "original_date": session["original_date"],
                "new_date": session["new_date_or_plan"],
                "reason": session["reason"]
            }
            requests.post(GAS_WEBHOOK_URL, json=payload)
            line_bot_api.push_message(
                LINE_ADMIN_USER_ID,
                TextSendMessage(text=f"📥 新申請：{session['type']}
原門診：{session['original_date']}
處理方式：{session['new_date_or_plan']}")
            )
            result = f"""✅ 已收到您的申請：
申請類型：{session['type']}
原門診：{session['original_date']}
處理方式：{session['new_date_or_plan']}
原因：{session['reason']}"""
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=result))
            del user_sessions[user_id]
        return
    else:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請輸入『主選單』來開始操作。"))

# ====== 處理檔案上傳 ======
@handler.add(MessageEvent, message=FileMessage)
def handle_file(event):
    file_name = event.message.file_name
    ext = file_name.split('.')[-1]
    message_content = line_bot_api.get_message_content(event.message.id)

    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tf:
        for chunk in message_content.iter_content():
            tf.write(chunk)
        temp_path = tf.name

    file_metadata = {'name': file_name, 'parents': [GOOGLE_DRIVE_FOLDER_ID]}
    media = MediaFileUpload(temp_path, resumable=True)
    uploaded = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"✅ 檔案已成功上傳至雲端硬碟！"))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
