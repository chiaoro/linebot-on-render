from flask import Flask, request, abort, jsonify
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from linebot.models import *
import os, json, tempfile, requests, mimetypes, smtplib
from email.mime.text import MIMEText
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from dotenv import load_dotenv
from utils.line_push import push_text_to_user
from utils.schedule_utils import handle_submission
from utils.google_auth import get_gspread_client
from utils.google_sheets import log_meeting_reply, get_doctor_name
from utils.state_manager import set_state, get_state, clear_state

load_dotenv()
app = Flask(__name__)

line_bot_api = LineBotApi(os.environ['LINE_CHANNEL_ACCESS_TOKEN'])
handler = WebhookHandler(os.environ['LINE_CHANNEL_SECRET'])

EMAIL_SENDER = "surry318@gmail.com"
EMAIL_RECEIVER = "surry318@gmail.com"
EMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")

SCOPE = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds_dict = json.loads(os.environ.get("GOOGLE_CREDENTIALS"))
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
gc = gspread.authorize(creds)

# 相關試算表
DOCTOR_SHEET_URL = "https://docs.google.com/spreadsheets/d/1fHf5XlbvLMd6ytAh_t8Bsi5ghToiQHZy1NlVfEG7VIo/edit"
RECORD_SHEET_URL = "https://docs.google.com/spreadsheets/d/1-mI71sC7TE-f8Gb9YPddhVGJrozKxLIdJlSBf2khJsA/edit"
spreadsheet = gc.open_by_key("1fHf5XlbvLMd6ytAh_t8Bsi5ghToiQHZy1NlVfEG7VIo")
mapping_sheet = spreadsheet.worksheet("UserMapping")

user_sessions = {}


def get_main_menu():
    return FlexSendMessage("主選單", {
        "type": "bubble",
        "body": {
            "type": "box", "layout": "vertical", "contents": [
                {"type": "text", "text": "📋 請選擇服務類別", "weight": "bold", "size": "lg", "margin": "md"},
                *[
                    {"type": "button", "action": {"type": "message", "label": label, "text": label},
                     "style": "primary", "margin": "md"}
                    for label in ["門診調整服務", "支援醫師服務", "新進醫師服務", "其他表單服務"]
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
support_buttons = [{"type": "button", "action": {"type": "uri", "label": "必填資料", "uri": "https://docs.google.com/forms/d/e/1FAIpQLSe0uYZEF2-bBY14_nKlykFuV__CEeEeOaGVrQJiai9cVoZWLQ/viewform"}, "style": "secondary", "margin": "md"},
                   {"type": "button", "action": {"type": "message", "label": "支援醫師調診單", "text": "支援醫師調診單"},"style": "primary", "margin": "md"}]
newcomer_buttons = [
    {"type": "button", "action": {"type": "uri", "label": "必填資料", "uri": "https://docs.google.com/forms/d/e/1FAIpQLScUn1Bm83wZ7SSTYCl8fj7z3b_sq7tscrZiXSt_AXOHf0SKPw/viewform"}, "style": "secondary", "margin": "md"},
    {"type": "button", "action": {"type": "uri", "label": "新進須知", "uri": "https://docs.google.com/forms/d/e/1FAIpQLSfH7139NRH2SbV8BjRBioXHtD_6KLMYtfmktJxEBxUc7OW3Kg/viewform"}, "style": "secondary", "margin": "md"}
]
other_buttons = [
    {"type": "button", "action": {"type": "uri", "label": "Temp傳檔", "uri": "https://docs.google.com/forms/d/e/1FAIpQLSexoPBHmJYpBlz_IIsSIO2GIB74dOR2FKPu7FIKjAmKIAqOcw/viewform"}, "style": "secondary", "margin": "md"},
    {"type": "button", "action": {"type": "uri", "label": "專師每日服務量填寫", "uri": "https://forms.office.com/Pages/ResponsePage.aspx?id=qul4xIkgo06YEwYZ5A7JD8YDS5UtAC5Gqgno_TUvnw1UQk1XR0MyTzVRNFZIOTcxVVFRSFdIMkQ1Ti4u"}, "style": "secondary", "margin": "md"},
    {"type": "button", "action": {"type": "uri", "label": "在職證明申請表", "uri": "https://docs.google.com/forms/d/e/1FAIpQLSeI64Av1Fb2Qgm6lCwTaUyvFRejHItS5KTQNujs1rU3NufMEA/viewform?usp=header"}, "style": "secondary", "margin": "md"},
    {"type": "button", "action": {"type": "uri", "label": "外科醫師休假登記表", "uri": "https://docs.google.com/forms/d/e/1FAIpQLScT2xDChXI7jBVPAf0rzKmtTXXtbZ6JFFD7EGfhmAvwSVfYzQ/viewform"}, "style": "secondary", "margin": "md"},
    {"type": "button", "action": {"type": "message", "label": "院務會議請假", "text": "院務會議請假"},  "style": "secondary",  "margin": "md"}
]





@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    user_msg = event.message.text.strip()

    # ✅ 主選單
    if user_msg == "主選單":
        try:
            line_bot_api.reply_message(event.reply_token, get_main_menu())
        except LineBotApiError:
            line_bot_api.push_message(user_id, get_main_menu())
        return

    # ✅ 四大選單分類
    submenu_map = {
        "門診調整服務": clinic_buttons,
        "支援醫師服務": support_buttons,
        "新進醫師服務": newcomer_buttons,
        "其他表單服務": other_buttons
    }
    if user_msg in submenu_map:
        try:
            line_bot_api.reply_message(event.reply_token, get_submenu(user_msg, submenu_map[user_msg]))
        except LineBotApiError:
            line_bot_api.push_message(user_id, get_submenu(user_msg, submenu_map[user_msg]))
        return

    # ✅ 院務會議請假流程
    if "院務會議" in user_msg:
        set_state(user_id, "ASK_LEAVE")
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請問你這禮拜院務會議是否能出席？請輸入 Y 或 N"))
        return

    if get_state(user_id) == "ASK_LEAVE":
        if user_msg.upper() == "Y":
            doctor_name = get_doctor_name(DOCTOR_SHEET_URL, user_id)
            log_meeting_reply(RECORD_SHEET_URL, user_id, doctor_name, "出席")
            clear_state(user_id)
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="收到您的回覆，您即將出席這禮拜院務會議，請當日準時與會。"))
        elif user_msg.upper() == "N":
            set_state(user_id, "ASK_REASON")
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請問您無法出席的原因是？"))
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請輸入 Y 或 N"))
        return

    if get_state(user_id) == "ASK_REASON":
        doctor_name = get_doctor_name(DOCTOR_SHEET_URL, user_id)
        log_meeting_reply(RECORD_SHEET_URL, user_id, doctor_name, "請假", user_msg)
        clear_state(user_id)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"收到回覆，原因：{user_msg}"))
        return

    # ✅ 調診三步驟流程
    if user_msg in ["我要調診", "我要休診", "我要代診", "我要加診"]:
        user_sessions[user_id] = {"step": 1, "type": user_msg}
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請問原本門診是哪一天？（例如 5/6 上午診）"))
        return

    if user_id in user_sessions:
        session = user_sessions[user_id]
        step = session["step"]
        if step == 1:
            session["original_date"] = user_msg
            session["step"] = 2
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請問您希望如何處理？例如:(5/23 下午診)(休診)(5/23 下午加診)(XXX代診)"))
        elif step == 2:
            session["new_date"] = user_msg
            session["step"] = 3
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請問原因是什麼？"))
        elif step == 3:
            session["reason"] = user_msg
            # 傳送到 Apps Script webhook（請改為你的）
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
        return

    
    # ✅ 支援醫師調診單 三步驟流程（要放在門診調整之前）
    if user_id in user_sessions and user_sessions[user_id].get("type") == "支援醫師調診單":
        session = user_sessions[user_id]
        step = session["step"]
        if step == 1:
            session["original_date"] = user_msg
            session["step"] = 2
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="⚙️ 請問您希望如何處理？（例如：加診、取消、代診）"))
        elif step == 2:
            session["new_date"] = user_msg
            session["step"] = 3
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="📝 最後，請輸入原因（例如：需返台、會議重疊）"))
        elif step == 3:
            session["reason"] = user_msg
            webhook_url = "https://script.google.com/macros/s/AKfycbw-zcC912rPhWM7Wfh0QFPNUVCeP-PCfv5YOrW10YocztjGz-Bz0JOZb_g2jX5VeZ0yog/exec"
            requests.post(webhook_url, json={
                "user_id": user_id,
                "request_type": "支援醫師調診單",
                "original_date": session["original_date"],
                "new_date": session["new_date"],
                "reason": session["reason"]
            })
            line_bot_api.reply_message(event.reply_token, TextSendMessage(
                text=f"""✅ 已收到您的申請（支援醫師調診單）：
原門診：{session['original_date']}
處理方式：{session['new_date']}
原因：{session['reason']}"""
            ))
            del user_sessions[user_id]
        return










@app.route("/callback", methods=['POST'])
def callback():
    try:
        data = request.get_json(force=True)
    except:
        data = {}

    if data.get("mode") == "push":
        user_id = data.get("userId")
        message = data.get("message", "（無訊息內容）")
        line_bot_api.push_message(user_id, TextSendMessage(text=message))
        return "Pushed message to user."

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
        handle_submission(name, off_days)
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/", methods=["GET"])
def home():
    return "LINE Bot is running"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"✅ Flask app starting on port {port}")
    app.run(host="0.0.0.0", port=port)
