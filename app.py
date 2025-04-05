from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import *
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import tempfile, os, json, datetime, requests
import mimetypes
import json
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from utils.line_push import push_text_to_user
from utils.schedule_utils import handle_submission, send_form_to_all_users, check_unsubmitted, remind_unsubmitted
from utils.google_auth import get_gspread_client




app = Flask(__name__)

# ✅ LINE 憑證
line_bot_api = LineBotApi(os.environ['LINE_CHANNEL_ACCESS_TOKEN'])
handler = WebhookHandler(os.environ['LINE_CHANNEL_SECRET'])
ADMIN_USER_ID = os.environ['LINE_ADMIN_USER_ID']

# ✅Google Sheets 認證與初始化（休假登記表）
SCOPE = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds_dict = json.loads(os.environ.get("GOOGLE_CREDENTIALS"))
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
gc = gspread.authorize(creds)

# ✅開啟 Google 試算表與工作表
spreadsheet_url = 'https://docs.google.com/spreadsheets/d/1_i-sQDdRGkuQSqTfUV4AZNcijY4xr8sukmh5mURFrAA/edit'
sheet = gc.open_by_url(spreadsheet_url).worksheet('line_users')

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
    name = event.message.text.strip()

    # 取得所有已綁定姓名
    gc = get_gspread_client()
    sheet = gc.open_by_url(os.getenv("FORM_RESPONSES_SHEET_URL")).worksheet('line_users')
    existing_names = sheet.col_values(2)

    if name in existing_names:
        reply = f"✅ {name} 已綁定過囉！"
    else:
        sheet.append_row([user_id, name, datetime.now().strftime("%Y/%m/%d %H:%M:%S")])
        reply = f"✅ 綁定成功！您好，{name}。"

    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))





# ✅ Google Drive 上傳初始化
SERVICE_ACCOUNT_INFO = json.loads(os.environ['GOOGLE_CREDENTIALS'])
SCOPES = ['https://www.googleapis.com/auth/drive.file']
credentials = service_account.Credentials.from_service_account_info(SERVICE_ACCOUNT_INFO, scopes=SCOPES)
drive_service = build('drive', 'v3', credentials=credentials)
UPLOAD_FOLDER_ID = '14LThiRWDO8zW7C0qrtobAVPrO_sAQtCW'

# ✅ 上傳檔案至 Google Drive
def upload_to_drive(file_path, file_name):
    folder_id = os.environ.get("GOOGLE_FOLDER_ID")
    if not folder_id:
        raise ValueError("Missing GOOGLE_FOLDER_ID environment variable.")

    file_metadata = {
        'name': file_name,
        'parents': [folder_id]
    }

    # 自動偵測 mimetype
    mimetype = mimetypes.guess_type(file_path)[0] or 'application/octet-stream'
    media = MediaFileUpload(file_path, mimetype=mimetype, resumable=True)

    try:
        uploaded_file = drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()
        return uploaded_file.get('id')
    except HttpError as error:
        print(f"❌ 上傳失敗：{error}")
        return None


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
other_buttons = [
    {"type": "button", "action": {"type": "message", "label": "Temp 傳檔(此功能尚在測試中)", "text": "我要上傳檔案"}, "style": "secondary", "margin": "md"},
    {"type": "button", "action": {"type": "uri", "label": "專師每日服務量填寫", "uri": "https://forms.office.com/Pages/ResponsePage.aspx?id=qul4xIkgo06YEwYZ5A7JD8YDS5UtAC5Gqgno_TUvnw1UQk1XR0MyTzVRNFZIOTcxVVFRSFdIMkQ1Ti4u"}, "style": "secondary", "margin": "md"}
]

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
            ask = "請問您要調整到哪一天？（例如：5/12 上午診）" if session["type"] == "我要調診" else "請問您希望如何處理？(例如休診、XXX醫師代診)"
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
            line_bot_api.reply_message(event.reply_token, TextSendMessage(
                text=f"""✅ 已收到您的申請：
申請類型：{session['type']}
原門診：{session['original_date']}
處理方式：{session['new_date']}
原因：{session['reason']}"""
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
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"""✅ 檔案已成功上傳至雲端"""))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
