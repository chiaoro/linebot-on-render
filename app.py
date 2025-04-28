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
from utils.night_shift_fee import start_night_shift_fee_request, continue_night_shift_fee_request, daily_night_fee_reminder
from utils.night_shift_fee_generator import generate_night_fee_doc
from meeting_reminder import send_meeting_reminder
from monthly_reminder import send_monthly_fixed_reminders
from event_reminder import send_important_event_reminder
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
# 主選單按鈕標籤
main_menu_labels = ["門診調整服務", "值班調整服務", "支援醫師服務", "新進醫師服務", "其他表單服務"]
# 子選單按鈕設定
clinic_buttons = ["我要調診", "我要休診", "我要代診", "我要加診"]
duty_swap_buttons = ["值班調換", "值班代理"]
# 定義 clinic_buttons_text
clinic_buttons_text = clinic_buttons.copy()

support_buttons = [
    {"type": "button", "action": {"type": "uri", "label": "必填資料", "uri": "https://docs.google.com/forms/.../viewform"}, "style": "secondary"},
    {"type": "button", "action": {"type": "message", "label": "支援醫師調診單", "text": "支援醫師調診單"}, "style": "primary"}
]
newcomer_buttons = [
    {"type": "button", "action": {"type": "uri", "label": "必填資料", "uri": "https://docs.google.com/forms/.../viewform"}, "style": "secondary"},
    {"type": "button", "action": {"type": "uri", "label": "新進須知", "uri": "https://docs.google.com/forms/.../viewform"}, "style": "secondary"}
]
other_buttons = [
    {"type": "button", "action": {"type": "uri", "label": "院務會議請假", "uri": ""}, "style": "secondary"},
    {"type": "button", "action": {"type": "message", "label": "夜點費申請", "text": "夜點費申請"}, "style": "secondary"}
]

submenu_map = {
    "門診調整服務": clinic_buttons,
    "值班調整服務": duty_swap_buttons,
    "支援醫師服務": support_buttons,
    "新進醫師服務": newcomer_buttons,
    "其他表單服務": other_buttons
}

# Flex 產生函式
def get_main_menu():
    contents = {
        "type": "bubble",
        "body": {"type": "box", "layout": "vertical", "contents": [
            {"type": "text", "text": "📋 請選擇服務類別", "weight": "bold", "size": "lg"}
        ] + [
            {"type": "button", "action": {"type": "message", "label": label, "text": label}, "style": "primary", "margin": "md"}
            for label in main_menu_labels
        ]}
    }
    return FlexSendMessage("主選單", contents)

def get_submenu(title, button_defs):
    contents = {
        "type": "bubble",
        "body": {"type": "box", "layout": "vertical", "contents": [
            {"type": "text", "text": f"📂 {title}", "weight": "bold", "size": "lg"}
        ] + button_defs}
    }
    return FlexSendMessage(title, contents)

# meeting flex bubble
meeting_flex_bubble = {
    "type": "bubble",
    "size": "mega",
    "body": {
        "type": "box", "layout": "vertical", "spacing": "md", "contents": [
            {"type": "text", "text": "📋 院務會議請假", "weight": "bold", "size": "xl", "align": "center"},
            {"type": "text", "text": "請問您是否出席？", "wrap": True, "align": "center"},
            {"type": "box", "layout": "horizontal", "contents": [
                {"type": "button", "style": "primary", "action": {"type": "message", "label": "✅ 出席", "text": "✅ 出席"}},
                {"type": "button", "style": "primary", "color": "#FF6666", "action": {"type": "message", "label": "❌ 請假", "text": "❌ 請假"}}
            ]}
        ]
    }
}

# 訊息處理
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    text_in = event.message.text.strip()

    # 1) 主選單
    if text_in == "主選單":
        line_bot_api.reply_message(event.reply_token, get_main_menu())
        return
    # 2) 子選單
    if text_in in submenu_map:
        line_bot_api.reply_message(event.reply_token, get_submenu(text_in, submenu_map[text_in]))
        return
    # 3) 院務會議
    if text_in == "院務會議請假":
        line_bot_api.reply_message(event.reply_token, FlexSendMessage("院務會議請假", meeting_flex_bubble))
        return
    # 4) 夜點費申請
    if text_in == "夜點費申請":
        reply = start_night_shift_fee_request(user_id)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
        return
    if user_id in user_sessions and user_sessions[user_id].get("type") == "夜點費":
        reply = continue_night_shift_fee_request(user_id, text_in)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
        return
    # 5) 調診流程
    if text_in in clinic_buttons_text:
        user_sessions[user_id] = {"step":1, "type": text_in}
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="📅 請輸入原門診日期（如5/6上午診）"))
        return
    # ... 続く其他流程 ...
    # default
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text="⚠️ 無效指令，請輸入「主選單」重新開始。"))

# Webhook 回調
@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get('X-Line-Signature')
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"

# 定時任務路由
@app.route("/daily-check-meeting-leave", methods=["GET"])
def daily_check_meeting_leave(): run_meeting_leave_scheduler(line_bot_api); return "OK",200
@app.route("/monthly-reminder", methods=["GET"])
def monthly_reminder(): send_monthly_fixed_reminders(); return "OK",200
@app.route("/event-reminder", methods=["GET"])
def event_reminder(): send_important_event_reminder(); return "OK",200
@app.route("/daily-push", methods=["GET"])
def daily_push(): run_daily_push(); return "OK",200
@app.route("/night-shift-reminder", methods=["GET"])
def night_shift_reminder(): daily_night_fee_reminder(); return "OK",200
@app.route("/generate-night-fee-word", methods=["GET"])
def generate_night_fee_word(): url = generate_night_fee_doc(); push_text_to_group(os.getenv("All_doctor_group_id"), f"夜點費報表：{url}"); return url,200
@app.route("/submit", methods=["POST"])
def receive_form_submission(): data = request.get_json(); return jsonify(handle_submission(data.get("name"), data.get("off_days")))
@app.route("/ping", methods=["GET"])
def ping(): return "Bot awake!"
@app.route("/", methods=["GET"])
def home(): return "Running"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT",5000)))
