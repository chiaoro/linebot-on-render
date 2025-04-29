
# --- 標準函式庫
import os
import json
import tempfile
import requests
import mimetypes
import smtplib
from email.mime.text import MIMEText
from datetime import datetime

# --- 第三方套件
from flask import Flask, request, abort, jsonify
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from linebot.models import TextMessage, MessageEvent, TextSendMessage, FlexSendMessage
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv

# --- 自己寫的 utils 模組
from utils.line_push import push_text_to_user
from utils.schedule_utils import handle_submission
from utils.google_auth import get_gspread_client
from utils.google_sheets import log_meeting_reply, get_doctor_name
from utils.state_manager import set_state, get_state, clear_state
from utils.meeting_reminder import send_meeting_reminder
from utils.monthly_reminder import send_monthly_fixed_reminders
from utils.event_reminder import send_important_event_reminder
from utils.daily_notifier import run_daily_push
from utils.meeting_leave import handle_meeting_leave_response
from utils.meeting_leave_scheduler import run_meeting_leave_scheduler
from utils.gspread_client import gc
from utils.night_shift_fee import handle_night_shift_request, daily_night_fee_reminder
from utils.night_shift_fee_generator import run_generate_night_fee_word
from utils.meeting_leave_menu import get_meeting_leave_menu  # ✅ 新加的


# 載入 .env
load_dotenv()

# ✅ 初始化 Flask 和 LineBot API
app = Flask(__name__)
line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))

# ✅ Google Sheets 認證
SCOPE = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds_dict = json.loads(os.getenv("GOOGLE_CREDENTIALS"))
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
gc = gspread.authorize(creds)

# ✅ 固定網址設定
DOCTOR_SHEET_URL = "https://docs.google.com/spreadsheets/d/1fHf5XlbvLMd6ytAh_t8Bsi5ghToiQHZy1NlVfEG7VIo/edit"  # 使用者對照表
NIGHT_FEE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1rtoP3e7D4FPzXDqv0yIOqYE9gwsdmFQSccODkbTZVDs/edit"  # 夜點費申請表

# ✅ Global 記憶體
user_sessions = {}



# ✅ Flex 主選單
def get_main_menu():
    return FlexSendMessage(
        "主選單",
        {
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {"type": "text", "text": "📋 請選擇服務類別", "weight": "bold", "size": "lg", "margin": "md"},
                    *[
                        {"type": "button", "action": {"type": "message", "label": label, "text": label}, "style": "primary", "margin": "md"}
                        for label in ["門診調整服務", "值班調整服務", "支援醫師服務", "新進醫師服務", "其他表單服務"]
                    ]
                ]
            }
        }
    )

# ✅ 子選單定義
submenu_map = {
    "門診調整服務": [
        {"type": "button", "action": {"type": "message", "label": t, "text": t}, "style": "primary", "margin": "md"}
        for t in ["我要調診", "我要休診", "我要代診", "我要加診"]
    ],
    "值班調整服務": [
        {"type": "button", "action": {"type": "message", "label": "值班調換", "text": "值班調換"}, "style": "primary", "margin": "md"},
        {"type": "button", "action": {"type": "message", "label": "值班代理", "text": "值班代理"}, "style": "primary", "margin": "md"}
    ],
    "支援醫師服務": [
        {"type": "button", "action": {"type": "uri", "label": "必填資料", "uri": "https://docs.google.com/forms/d/e/1FAIpQLSe0uYZEF2-bBY14_nKlykFuV__CEeEeOaGVrQJiai9cVoZWLQ/viewform"}, "style": "secondary", "margin": "md"},
        {"type": "button", "action": {"type": "message", "label": "支援醫師調診單", "text": "支援醫師調診單"}, "style": "primary", "margin": "md"}
    ],
    "新進醫師服務": [
        {"type": "button", "action": {"type": "uri", "label": "必填資料", "uri": "https://docs.google.com/forms/d/e/1FAIpQLScUn1Bm83wZ7SSTYCl8fj7z3b_sq7tscrZiXSt_AXOHf0SKPw/viewform"}, "style": "secondary", "margin": "md"},
        {"type": "button", "action": {"type": "uri", "label": "新進須知", "uri": "https://docs.google.com/forms/d/e/1FAIpQLSfH7139NRH2SbV8BjRBioXHtD_6KLMYtfmktJxEBxUc7OW3Kg/viewform"}, "style": "secondary", "margin": "md"}
    ],
    "其他表單服務": [
        {"type": "button", "action": {"type": "uri", "label": "Temp傳檔", "uri": "https://docs.google.com/forms/d/e/1FAIpQLSexoPBHmJYpBlz_IIsSIO2GIB74dOR2FKPu7FIKjAmKIAqOcw/viewform"}, "style": "secondary", "margin": "md"},
        {"type": "button", "action": {"type": "uri", "label": "專師每日服務量填寫", "uri": "https://forms.office.com/Pages/ResponsePage.aspx?id=qul4xIkgo06YEwYZ5A7JD8YDS5UtAC5Gqgno_TUvnw1UQk1XR0MyTzVRNFZIOTcxVVFRSFdIMkQ1Ti4u"}, "style": "secondary", "margin": "md"},
        {"type": "button", "action": {"type": "uri", "label": "在職證明申請", "uri": "https://docs.google.com/forms/d/e/1FAIpQLSeI64Av1Fb2Qgm6lCwTaUyvFRejHItS5KTQNujs1rU3NufMEA/viewform"}, "style": "secondary", "margin": "md"},
        {"type": "button", "action": {"type": "uri", "label": "外科醫師休假登記表", "uri": "https://docs.google.com/forms/d/e/1FAIpQLScT2xDChXI7jBVPAf0rzKmtTXXtbZ6JFFD7EGfhmAvwSVfYzQ/viewform"}, "style": "secondary", "margin": "md"},
        {"type": "button", "action": {"type": "message", "label": "院務會議請假", "text": "院務會議請假"}, "style": "secondary", "margin": "md"},
        {"type": "button", "action": {"type": "message", "label": "夜點費申請", "text": "夜點費申請"}, "style": "secondary", "margin": "md"}
    ]
}

# ✅ 主訊息處理
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    user_msg = event.message.text.strip()

    # 夜點費處理
    if "夜點費" in user_msg:
        reply = handle_night_shift_request(user_id, user_msg)
        if reply:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
        return

    # 主選單處理
    if user_msg == "主選單":
        line_bot_api.reply_message(event.reply_token, get_main_menu())
        return

    # 子選單處理
    if user_msg in submenu_map:
        submenu = submenu_map[user_msg]
        line_bot_api.reply_message(event.reply_token, FlexSendMessage(user_msg, {
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [{"type": "text", "text": f"📂 {user_msg}", "weight": "bold", "size": "lg", "margin": "md"}] + submenu
            }
        }))
        return

    # ✅ 院務會議請假流程簡化版
    if user_msg == "院務會議出席":
        log_meeting_reply(user_id, "出席", "")
        clear_state(user_id)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="✅ 已紀錄您出席院務會議。"))
        return
    
    if user_msg == "院務會議請假申請":
        set_state(user_id, "ASK_REASON")
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請輸入您無法出席的原因："))
        return
    
    if get_state(user_id) == "ASK_REASON":
        reason = user_msg
        log_meeting_reply(user_id, "請假", reason)
        clear_state(user_id)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="✅ 已紀錄您的請假申請。"))
        return

    # 無效指令
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text="⚠️ 無效指令，請輸入『主選單』重新開始。"))




# ✅ LINE Webhook
@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get('X-Line-Signature')
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"

# ✅ 基本 home 路由
@app.route("/", methods=["GET"])
def home():
    return "LINE Bot is running!", 200

# ✅ 夜點費 Word 文件產生
@app.route("/generate-night-fee-word", methods=["GET"])
def generate_night_fee_word():
    try:
        from utils.night_shift_fee_generator import run_generate_night_fee_word
        run_generate_night_fee_word()
        return "✅ 夜點費申請表產生完成", 200
    except Exception as e:
        return f"❌ 夜點費申請表產生錯誤：{e}", 500

# ✅ 夜點費每日提醒
@app.route("/night-shift-reminder", methods=["GET"])
def night_shift_reminder():
    try:
        from utils.night_shift_fee import daily_night_fee_reminder
        daily_night_fee_reminder()
        return "✅ 夜點費每日提醒完成", 200
    except Exception as e:
        return f"❌ 夜點費每日提醒錯誤：{e}", 500

# ✅ 院務會議請假提醒推播
@app.route("/meeting-reminder", methods=["GET"])
def meeting_reminder():
    try:
        send_meeting_reminder()
        return "✅ 院務會議提醒完成", 200
    except Exception as e:
        return f"❌ 院務會議提醒錯誤：{e}", 500

# ✅ 固定日期推播
@app.route("/monthly-reminder", methods=["GET"])
def monthly_reminder():
    try:
        send_monthly_fixed_reminders()
        return "✅ 固定日期推播完成", 200
    except Exception as e:
        return f"❌ 固定推播錯誤：{e}", 500

# ✅ 重要會議推播
@app.route("/event-reminder", methods=["GET"])
def event_reminder():
    try:
        send_important_event_reminder()
        return "✅ 重要會議提醒完成", 200
    except Exception as e:
        return f"❌ 重要會議推播錯誤：{e}", 500

# ✅ 每日推播
@app.route("/daily-push", methods=["GET"])
def daily_push():
    try:
        run_daily_push()
        return "✅ 每日推播完成", 200
    except Exception as e:
        return f"❌ 每日推播錯誤：{e}", 500

# ✅ 院務會議請假表單提交
@app.route("/meeting-leave", methods=["POST"])
def meeting_leave():
    try:
        data = request.get_json()
        user_id = data.get("user_id")
        user_reply = data.get("reply")
        handle_meeting_leave_response(user_id, user_reply)
        return "✅ 院務會議請假已處理", 200
    except Exception as e:
        return f"❌ 院務會議請假處理錯誤：{e}", 500

# ✅ 院務會議請假排程推播
@app.route("/meeting-leave-scheduler", methods=["GET"])
def meeting_leave_scheduler():
    try:
        run_meeting_leave_scheduler()
        return "✅ 院務會議請假排程推播完成", 200
    except Exception as e:
        return f"❌ 院務會議請假排程錯誤：{e}", 500

# ✅ ping 喚醒 Bot
@app.route("/ping", methods=["GET"])
def ping():
    return "Bot is awake!", 200





# ✅ 申請值班調整表單接收（submit-duty-swap）
@app.route("/submit-duty-swap", methods=["POST"])
def submit_duty_swap():
    try:
        data = request.get_json()
        doctor_name = data.get("doctor_name")
        off_days = data.get("off_days")
        if not doctor_name or not off_days:
            return jsonify({"status": "error", "message": "缺少欄位"}), 400
        handle_submission(doctor_name, off_days)
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# ✅ 錯誤處理測試
@app.route("/error-handler", methods=["GET"])
def error_handler():
    try:
        raise Exception("測試錯誤")
    except Exception as e:
        return f"❌ 錯誤發生：{str(e)}", 500

# ✅ 啟動 Flask 伺服器
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # 預設 port 5000
    print(f"✅ Flask app starting on port {port}")
    app.run(host="0.0.0.0", port=port)


