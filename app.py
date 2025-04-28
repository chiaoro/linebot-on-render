# app.py
from flask import Flask, request, abort, jsonify
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import TextMessage, MessageEvent, TextSendMessage, FlexSendMessage
import os, json, requests
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv
from datetime import datetime, timedelta

# utils imports
from utils.line_push_utils import push_text_to_user, push_text_to_group
from utils.schedule_utils import handle_submission
from utils.google_auth import get_gspread_client
from utils.google_sheets import log_meeting_reply, get_doctor_name
from utils.state_manager import set_state, get_state, clear_state
from utils.night_shift_fee import handle_night_shift_request, daily_night_fee_reminder
from utils.night_shift_fee_generator import generate_night_fee_doc
from meeting_reminder import run_meeting_reminder
from monthly_reminder import run_monthly_reminder
from event_reminder import run_event_reminder
from daily_notifier import run_daily_push
from meeting_leave import handle_meeting_leave_response
from meeting_leave_scheduler import run_meeting_leave_scheduler

# initialize app and LINE
load_dotenv()
app = Flask(__name__)
line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))

# authorize Google Sheets
creds_dict = json.loads(os.getenv("GOOGLE_CREDENTIALS", "{}"))
scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
gc = gspread.authorize(creds)

# global sessions
user_sessions = {}
user_votes = {}
stat_active = {}

# --- Flex menu definitions ---
main_menu_labels = ["門診調整服務", "值班調整服務", "支援醫師服務", "新進醫師服務", "其他表單服務"]
clinic_buttons_text = ["我要調診", "我要休診", "我要代診", "我要加診"]
duty_buttons_text = ["值班調換", "值班代理"]

support_buttons = [
    {"type":"button","action":{"type":"uri","label":"必填資料","uri":"https://docs.google.com/forms/d/e/1FAIpQLSe0uYZEF2-bBY14_nKlykFuV__CEeEeOaGVrQJiai9cVoZWLQ/viewform"},"style":"secondary","margin":"md"},
    {"type":"button","action":{"type":"message","label":"支援醫師調診單","text":"支援醫師調診單"},"style":"primary","margin":"md"}
]
newcomer_buttons = [
    {"type":"button","action":{"type":"uri","label":"必填資料","uri":"https://docs.google.com/forms/d/e/1FAIpQLScUn1Bm83wZ7SSTYCl8fj7z3b_sq7tscrZiXSt_AXOHf0SKPw/viewform"},"style":"secondary","margin":"md"},
    {"type":"button","action":{"type":"uri","label":"新進須知","uri":"https://docs.google.com/forms/d/e/1FAIpQLSfH7139NRH2SbV8BjRBioXHtD_6KLMYtfmktJxEBxUc7OW3Kg/viewform"},"style":"secondary","margin":"md"}
]
other_buttons = [
    {"type":"button","action":{"type":"message","label":"院務會議請假","text":"院務會議請假"},"style":"secondary","margin":"md"},
    {"type":"button","action":{"type":"message","label":"夜點費申請","text":"夜點費申請"},"style":"secondary","margin":"md"},
    {"type":"button","action":{"type":"message","label":"在職證明申請","text":"在職證明申請"},"style":"secondary","margin":"md"},
    {"type":"button","action":{"type":"uri","label":"專師每日服務量填寫","uri":"https://forms.office.com/Pages/ResponsePage.aspx?id=qul4xIkgo06YEwYZ5A7JD8YDS5UtAC5Gqgno_TUvnw1UQk1XR0MyTzVRNFZIOTcxVVFRSFdIMkQ1Ti4u"},"style":"secondary","margin":"md"},
    {"type":"button","action":{"type":"uri","label":"Temp傳檔","uri":"https://docs.google.com/forms/d/e/1FAIpQLSexoPBHmJYpBlz_IIsSIO2GIB74dOR2FKPu7FIKjAmKIAqOcw/viewform"},"style":"secondary","margin":"md"},
    {"type":"button","action":{"type":"uri","label":"外科醫師休假登記表","uri":"https://docs.google.com/forms/d/e/1FAIpQLScT2xDChXI7jBVPAf0rzKmtTXXtbZ6JFFD7EGfhmAvwSVfYzQ/viewform"},"style":"secondary","margin":"md"}
]

submenu_map = {
    "門診調整服務": clinic_buttons_text,
    "值班調整服務": duty_buttons_text,
    "支援醫師服務": support_buttons,
    "新進醫師服務": newcomer_buttons,
    "其他表單服務": other_buttons
}

# Flex generators

def get_main_menu():
    bubble = {
        "type": "bubble",
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {"type": "text", "text": "📋 請選擇服務類別", "weight": "bold", "size": "lg"},
            ] + [
                {"type": "button", "action": {"type": "message", "label": label, "text": label}, "style": "primary", "margin": "md"}
                for label in main_menu_labels
            ]
        }
    }
    return FlexSendMessage("主選單", bubble)

def get_submenu(title, items):
    if all(isinstance(i, str) for i in items):
        buttons = [
            {"type": "button", "action": {"type": "message", "label": i, "text": i}, "style": "primary", "margin": "md"}
            for i in items
        ]
    else:
        buttons = items
    bubble = {
        "type": "bubble",
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {"type": "text", "text": f"📂 {title}", "weight": "bold", "size": "lg"},
            ] + buttons
        }
    }
    return FlexSendMessage(title, bubble)

meeting_flex_bubble = {
    "type": "bubble",
    "size": "mega",
    "body": {
        "type": "box",
        "layout": "vertical",
        "spacing": "md",
        "contents": [
            {"type": "text", "text": "📋 院務會議請假", "weight": "bold", "size": "xl", "align": "center"},
            {"type": "text", "text": "請問您是否出席？", "wrap": True, "align": "center"},
            {
                "type": "box",
                "layout": "horizontal",
                "spacing": "md",
                "contents": [
                    {"type": "button", "style": "primary", "action": {"type": "message", "label": "✅ 出席", "text": "✅ 出席"}},
                    {"type": "button", "style": "primary", "color": "#FF6666", "action": {"type": "message", "label": "❌ 請假", "text": "❌ 請假"}}
                ]
            }
        ]
    }
}

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    text = event.message.text.strip()

    # 1. 主選單
    if text == "主選單":
        return line_bot_api.reply_message(event.reply_token, get_main_menu())
    # 2. 子選單
    if text in submenu_map:
        return line_bot_api.reply_message(event.reply_token, get_submenu(text, submenu_map[text]))
    # 3. 院務會議請假
    if text == "院務會議請假":
        return line_bot_api.reply_message(event.reply_token, FlexSendMessage("院務會議請假", meeting_flex_bubble))
    # 4. 夜點費申請
    if text == "夜點費申請":
        reply = handle_night_shift_request(event)
        return line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
    # 5. 調診流程
    if text in clinic_buttons_text:
        user_sessions[user_id] = {"step": 1, "type": text}
        return line_bot_api.reply_message(event.reply_token, TextSendMessage(text="📅 請輸入原門診日期（如5/6上午診）"))
    # 6. 值班調整流程
    if text in duty_buttons_text:
        user_sessions[user_id] = {"step": 1, "type": text}
        return line_bot_api.reply_message(event.reply_token, TextSendMessage(text="🟡 請問值班班別？"))
    # 7. 在職證明申請
    if text == "在職證明申請":
        return line_bot_api.reply_message(event.reply_token, TextSendMessage(text="📄 在職證明申請表：https://docs.google.com/forms/d/e/1FAIpQLSeI64Av1Fb2Qgm6lCwTaUyvFRejHItS5KTQNujs1rU3NufMEA/viewform"))
    # 8. 專師每日服務量填寫
    if text == "專師每日服務量填寫":
        return line_bot_api.reply_message(event.reply_token, TextSendMessage(text="📋 專師每日服務量填寫表單：https://forms.office.com/Pages/ResponsePage.aspx?id=qul4xIkgo06YEwYZ5A7JD8YDS5UtAC5Gqgno_TUvnw1UQk1XR0MyTzVRNFZIOTcxVVFRSFdIMkQ1Ti4u"))
    # 9. Temp傳檔
    if text == "Temp傳檔":
        return line_bot_api.reply_message(event.reply_token, TextSendMessage(text="📂 Temp傳檔表單：https://docs.google.com/forms/d/e/1FAIpQLSexoPBHmJYpBlz_IIsSIO2GIB74dOR2FKPu7FIKjAmKIAqOcw/viewform"))
    # 10. 外科醫師休假登記表
    if text == "外科醫師休假登記表":
        return line_bot_api.reply_message(event.reply_token, TextSendMessage(text="📅 外科醫師休假登記表單：https://docs.google.com/forms/d/e/1FAIpQLScT2xDChXI7jBVPAf0rzKmtTXXtbZ6JFFD7EGfhmAvwSVfYzQ/viewform"))
    # default
    return line_bot_api.reply_message(event.reply_token, TextSendMessage(text="⚠️ 無效指令，請輸入「主選單」重新開始。"))

# Webhook
@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature")
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"

# 定時任務路由
@app.route("/daily-check-meeting-leave", methods=["GET"])
def daily_check_meeting_leave():
    run_meeting_leave_scheduler(line_bot_api)
    return "OK",200

@app.route("/meeting-reminder", methods=["GET"])
def meeting_reminder():
    run_meeting_reminder()
    return "OK",200

@app.route("/monthly-reminder", methods=["GET"])
def monthly_reminder():
    run_monthly_reminder()
    return "OK",200

@app.route("/event-reminder", methods=["GET"])
def event_reminder():
    run_event_reminder()
    return "OK",200

@app.route("/daily-push", methods=["GET"])
def daily_push():
    run_daily_push()
    return "OK",200

@app.route("/night-shift-reminder", methods=["GET"])
def night_shift_reminder():
    daily_night_fee_reminder()
    return "OK",200

@app.route("/generate-night-fee-word", methods=["GET"])
def generate_night_fee_word():
    url = generate_night_fee_doc()
    push_text_to_group(os.getenv("All_doctor_group_id"), f"夜點費報表：{url}")
    return url,200

@app.route("/submit", methods=["POST"])
def receive_form_submission():
    data = request.get_json()
    result = handle_submission(data.get("name"), data.get("off_days"))
    return jsonify(result)

@app.route("/ping", methods=["GET"])
def ping():
    return "Bot is awake!",200

@app.route("/", methods=["GET"])
def home():
    return "LINE Bot is running!",200

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
