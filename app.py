from flask import Flask, request, abort, jsonify
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
from linebot.models import MessageEvent, TextMessage, TextSendMessage, FlexSendMessage
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from utils.line_push import push_text_to_user
from utils.schedule_utils import handle_submission
from utils.google_auth import get_gspread_client
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv
from utils.google_sheets import log_meeting_reply, get_doctor_name
from utils.state_manager import set_state, get_state, clear_state




load_dotenv()
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

# 🧾 設定 Email 寄件資訊
EMAIL_SENDER = "surry318@gmail.com"
EMAIL_RECEIVER = "surry318@gmail.com"
EMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")  # ⬅ 記得設為環境變數

# ✅ 名冊 Google Sheets 初始化
# REGISTER_SHEET_ID = os.environ.get("REGISTER_SHEET_ID")
# register_sheet = gc.open_by_key(REGISTER_SHEET_ID).worksheet("UserMapping")

# ✅院務會議請假
DOCTOR_SHEET_URL = "https://docs.google.com/spreadsheets/d/1fHf5XlbvLMd6ytAh_t8Bsi5ghToiQHZy1NlVfEG7VIo/edit"
RECORD_SHEET_URL = "https://docs.google.com/spreadsheets/d/1-mI71sC7TE-f8Gb9YPddhVGJrozKxLIdJlSBf2khJsA/edit"

# ✅Google Sheets 授權
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
service_account_info = json.loads(os.environ["GOOGLE_CREDENTIALS"])
creds = ServiceAccountCredentials.from_json_keyfile_dict(service_account_info, scope)
gc = gspread.authorize(creds)
spreadsheet = gc.open_by_key("1fHf5XlbvLMd6ytAh_t8Bsi5ghToiQHZy1NlVfEG7VIo")
mapping_sheet = spreadsheet.worksheet("UserMapping")

def is_user_registered(user_id):
    user_ids = register_sheet.col_values(2)
    return user_id in user_ids

def register_user(name, user_id):
    register_sheet.append_row([name, user_id])



def send_email(subject, body):
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = EMAIL_SENDER
    msg["To"] = EMAIL_RECEIVER

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL_SENDER, EMAIL_APP_PASSWORD)
        server.send_message(msg)







@app.route("/callback", methods=['POST'])
def callback():
    # 嘗試解析 JSON，如果是 Apps Script 傳來的 push 請求
    try:
        data = request.get_json(force=True)
    except:
        data = {}

    if data.get("mode") == "push":
        user_id = data.get("userId")
        message = data.get("message", "（無訊息內容）")
        line_bot_api.push_message(user_id, TextSendMessage(text=message))
        return "Pushed message to user."

    # 否則，當成 LINE 官方事件處理
    signature = request.headers.get("X-Line-Signature")
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return "OK"












@app.route("/submit", methods=["POST"])
def receive_form_submission():
    data = request.get_json()
    name = data.get("name")
    off_days = data.get("off_days")
    if not name or not off_days:
        return jsonify({"status": "error", "message": "缺少欄位"}), 400

    try:
        from utils.schedule_utils import handle_submission
        handle_submission(name, off_days)
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

def submit_data():
    data = request.get_json()
    name = data.get("name", "未填")
    department = data.get("department", "未填")
    status = data.get("status", "未填")

    # ✅ 寫入 Google Sheets（gspread / API 寫法略）
    worksheet.append_row([name, department, status])

    # ✅ 寄 Email 通知
    msg = f"📥 新資料紀錄：\n👤 姓名：{name}\n🏥 科別：{department}\n📌 狀態：{status}"
    send_email(subject="📬 有新資料寫入 Google Sheets", body=msg)

    return "Data saved & email sent!"





@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    user_msg = event.message.text.strip()
    


    # 綁定格式：「綁定 張巧柔 外科」
    if user_msg.startswith("綁定"):
        parts = user_msg.split()
        if len(parts) == 3:
            name = parts[1]
            dept = parts[2]

            # 檢查是否已綁定
            existing = mapping_sheet.col_values(1)
            if user_id in existing:
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="✅ 您已綁定過囉～"))
                return

            # 加入對照表
            mapping_sheet.append_row([user_id, name, dept])
            line_bot_api.reply_message(event.reply_token, TextSendMessage(
                text=f"✅ 綁定成功！歡迎 {name} 醫師（{dept}）"
            ))
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(
                text="請依格式輸入：\n綁定 張巧柔 醫療部"
            ))
        return



# ✅ 院務會議請假   
    original_text = event.message.text.strip()
    text = original_text.upper()

    if "院務會議" in original_text:
        set_state(user_id, "ASK_LEAVE")
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請問你這禮拜院務會議是否要請假？請輸入 Y 或 N"))
    elif get_state(user_id) == "ASK_LEAVE":
        if text == "Y":
            clear_state(user_id)
            doctor_name = get_doctor_name(DOCTOR_SHEET_URL, user_id)
            log_meeting_reply(RECORD_SHEET_URL, user_id, doctor_name, "出席")
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="收到您的回覆，\n您即將出席這禮拜院務會議。\n請當日準時與會。"))
        elif text == "N":
            set_state(user_id, "ASK_REASON")
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請問您這禮拜院務會議無法出席的請假原因是？"))
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請輸入有效選項：Y 或 N"))
    elif get_state(user_id) == "ASK_REASON":
        reason = original_text
        clear_state(user_id)
        doctor_name = get_doctor_name(DOCTOR_SHEET_URL, user_id)
        log_meeting_reply(RECORD_SHEET_URL, user_id, doctor_name, "請假", reason)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(
            text=f"收到您的回覆。\n你這禮拜無法出席會議。\n原因：{reason}"))
    elif "其他表單服務" in original_text:
        with open("utils/flex_menu.json", "r") as f:
            flex_data = json.load(f)
        flex_msg = FlexSendMessage(alt_text="其他表單服務", contents=flex_data)
        line_bot_api.reply_message(event.reply_token, flex_msg)







def get_user_info(user_id):
    records = mapping_sheet.get_all_records()
    for row in records:
        if row['LINE_USER_ID'] == user_id:
            return row['姓名'], row['科別']
    return None, None




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
    {"type": "button", "action": {"type": "uri", "label": "Temp傳檔", "uri": "https://docs.google.com/forms/d/e/1FAIpQLSexoPBHmJYpBlz_IIsSIO2GIB74dOR2FKPu7FIKjAmKIAqOcw/viewform?usp=header"}, "style": "secondary", "margin": "md"},
    {"type": "button", "action": {"type": "uri", "label": "專師每日服務量填寫", "uri": "https://forms.office.com/Pages/ResponsePage.aspx?id=qul4xIkgo06YEwYZ5A7JD8YDS5UtAC5Gqgno_TUvnw1UQk1XR0MyTzVRNFZIOTcxVVFRSFdIMkQ1Ti4u"}, "style": "secondary", "margin": "md"},
    {"type": "button", "action": {"type": "uri", "label": "外科醫師休假登記表", "uri": "https://docs.google.com/forms/d/e/1FAIpQLScT2xDChXI7jBVPAf0rzKmtTXXtbZ6JFFD7EGfhmAvwSVfYzQ/viewform?usp=sharing"}, "style": "secondary", "margin": "md"},
    {"type": "button", "action": {"type": "message", "label": "院務會議請假", "text": "院務會議請假"},  "style": "secondary",  "margin": "md"}
]

@app.route("/", methods=["GET"])
def home():
    return "LINE Bot is running"






    # ⬇️ 加在這裡：檢查是否為第一次輸入姓名的使用者
    if not is_user_registered(user_id):
        register_user(text, user_id)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"✅ 您好 {text}，已完成綁定！"))
        return




    
    elif text == "門診調整服務":
        line_bot_api.reply_message(event.reply_token, get_submenu("門診調整選單", clinic_buttons))
    elif text == "支援醫師服務":
        line_bot_api.reply_message(event.reply_token, get_submenu("支援醫師服務", support_buttons))
    elif text == "新進醫師服務":
        line_bot_api.reply_message(event.reply_token, get_submenu("新進醫師服務", newcomer_buttons))
    elif text == "主選單":
        try:
            line_bot_api.reply_message(event.reply_token, get_main_menu())
        except LineBotApiError:
            line_bot_api.push_message(user_id, get_main_menu())
    elif text == "其他表單服務":
        line_bot_api.reply_message(event.reply_token, get_submenu("其他表單服務", other_buttons))
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

    






if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
