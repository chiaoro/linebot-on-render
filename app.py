# === 標準函式庫 ===
import os
import re
import json
import tempfile
import requests
import mimetypes
import smtplib
from email.mime.text import MIMEText
from datetime import datetime

# === 第三方套件 ===
from flask import Flask, request, abort, jsonify
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from linebot.models import (
    TextMessage, MessageEvent, TextSendMessage, FlexSendMessage
)
import gspread
from google.oauth2 import service_account
from dotenv import load_dotenv
from googleapiclient.discovery import build
# === 自訂 utils 模組 ===

# 👉 LINE 處理工具
from utils.line_push import push_text_to_user
from utils.line_utils import get_event_text, is_trigger, is_stat_trigger

# 👉 使用者狀態與綁定
from utils.state_manager import set_state, get_state, clear_state
from utils.user_binding import (
    handle_user_binding,
    send_bind_start_flex,
    ask_for_name,
    confirm_binding,
    ensure_user_id_exists,
    user_states
)
from utils.session_manager import get_session, set_session, clear_session, user_sessions

# 👉 Google Sheets 操作
from utils.gspread_client import get_gspread_client
from utils.google_sheets import get_doctor_info, get_doctor_name, log_meeting_reply

# 👉 日期與文字處理
from utils.date_utils import expand_date_range

# 👉 Flex Bubble 模板
from utils.bubble_templates import main_menu_v2_bubble
from utils.flex_templates import (
    get_adjustment_bubble,
    get_duty_swap_bubble,
    get_support_adjustment_bubble
)

# 👉 院務會議請假
from utils.meeting_leave import handle_meeting_leave_response
from utils.meeting_leave_menu import get_meeting_leave_menu, get_meeting_leave_success
from utils.meeting_leave_scheduler import run_meeting_leave_scheduler

# 👉 夜點費提醒與產出
from utils.night_shift_fee import handle_night_shift_request, daily_night_fee_reminder, run_night_shift_reminder
from utils.daily_night_fee_reminder import send_night_fee_reminders
from utils.night_shift_fee_generator import generate_night_fee_docs

# 👉 表單填寫處理（值班、休診、問卷）
from utils.schedule_utils import handle_submission

# 👉 群組投票（如需啟用）
from utils.group_vote_tracker import handle_group_vote

# === handlers 分流功能模組 ===

from handlers.duty_handler import handle_duty_message                  # 值班調整（調換與代理）
from handlers.meeting_leave_handler import handle_meeting_leave        # 院務會議請假主處理
from handlers.night_fee_handler import handle_night_fee                # 夜點費申請主處理
from handlers.support_adjust_handler import handle_support_adjustment  # 支援醫師調診流程
from handlers.adjust_handler import handle_adjustment                  # 門診異動處理
from handlers.stats_handler import handle_stats                        # 📊 群組統計功能
from utils.line_utils import get_event_text, get_safe_user_name
# ✅ 醫師查詢
from handlers.doctor_query_handler import handle_doctor_query
from handlers.overtime_handler import handle_overtime
from linebot.models import PostbackEvent
from handlers.overtime_handler import submit_overtime



# ✅載入 .env
load_dotenv()

# ✅ 初始化 Flask 和 LineBot API
app = Flask(__name__)
line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))

# ✅ Google Sheets 認證
SCOPE = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds_dict = json.loads(os.getenv("GOOGLE_CREDENTIALS"))
gc = get_gspread_client()

# ✅ 固定網址設定
DOCTOR_SHEET_URL = "https://docs.google.com/spreadsheets/d/1fHf5XlbvLMd6ytAh_t8Bsi5ghToiQHZy1NlVfEG7VIo/edit"  # 使用者對照表
NIGHT_FEE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1rtoP3e7D4FPzXDqv0yIOqYE9gwsdmFQSccODkbTZVDs/edit"  # 夜點費申請表

# ✅ 白名單（僅允許特定 user_id 使用）
ALLOWED_USER_IDS = os.getenv("ALLOWED_USER_IDS", "").split(",")



# ✅ 工具函式（這是你自己寫的，要放在這裡）
def is_trigger(event, keywords):
    if event.type == "message" and isinstance(event.message, TextMessage):
        return any(event.message.text.strip() == kw for kw in keywords)
    elif event.type == "postback":
        return any(event.postback.data.strip() == kw for kw in keywords)
    return False






# ✅ Flex 主選單
# ✅ 子選單定義
submenu_map = {
    "門診調整服務": [
        {"type": "button", "action": {"type": "message", "label": t, "text": t}, "style": "primary","color": "#84c99c", "margin": "md"}
        for t in ["我要調診", "我要休診", "我要代診", "我要加診"]
    ],
    "值班調整服務": [
        {"type": "button", "action": {"type": "message", "label": "值班調換", "text": "值班調換"}, "style": "primary","color": "#d09a7d", "margin": "md"},
        {"type": "button", "action": {"type": "message", "label": "值班代理", "text": "值班代理"}, "style": "primary","color": "#d09a7d", "margin": "md"}
    ],
    "支援醫師服務": [
        {"type": "button", "action": {"type": "uri", "label": "必填資料", "uri": "https://docs.google.com/forms/d/e/1FAIpQLSe0uYZEF2-bBY14_nKlykFuV__CEeEeOaGVrQJiai9cVoZWLQ/viewform"}, "style": "secondary","color": "#80a09d", "margin": "md"},
        {"type": "button", "action": {"type": "message", "label": "支援醫師調診單", "text": "支援醫師調診單"}, "style": "primary","color": "#80a09d", "margin": "md"}
    ],
    "新進醫師服務": [
        {"type": "button", "action": {"type": "uri", "label": "必填資料", "uri": "https://docs.google.com/forms/d/e/1FAIpQLScUn1Bm83wZ7SSTYCl8fj7z3b_sq7tscrZiXSt_AXOHf0SKPw/viewform"}, "style": "secondary","color": "#db9fb2", "margin": "md"},
        {"type": "button", "action": {"type": "uri", "label": "新進須知", "uri": "https://docs.google.com/forms/d/e/1FAIpQLSfH7139NRH2SbV8BjRBioXHtD_6KLMYtfmktJxEBxUc7OW3Kg/viewform"}, "style": "secondary","color": "#db9fb2", "margin": "md"}
    ],

    "其他表單服務": [
        {"type": "button", "action": {"type": "uri", "label": "Temp傳檔", "uri": "https://docs.google.com/forms/d/e/1FAIpQLSexoPBHmJYpBlz_IIsSIO2GIB74dOR2FKPu7FIKjAmKIAqOcw/viewform"}, "style": "secondary","color": "#ee9382", "margin": "md"},
        {"type": "button", "action": {"type": "uri", "label": "專師每日服務量填寫", "uri": "https://forms.office.com/Pages/ResponsePage.aspx?id=qul4xIkgo06YEwYZ5A7JD8YDS5UtAC5Gqgno_TUvnw1UQk1XR0MyTzVRNFZIOTcxVVFRSFdIMkQ1Ti4u"}, "style": "secondary","color": "#ee9382", "margin": "md"},
        {"type": "button", "action": {"type": "uri", "label": "在職證明申請", "uri": "https://docs.google.com/forms/d/e/1FAIpQLSeI64Av1Fb2Qgm6lCwTaUyvFRejHItS5KTQNujs1rU3NufMEA/viewform"}, "style": "secondary","color": "#ee9382", "margin": "md"},
        {"type": "button", "action": {"type": "uri", "label": "外科醫師休假登記表", "uri": "https://docs.google.com/forms/d/e/1FAIpQLScT2xDChXI7jBVPAf0rzKmtTXXtbZ6JFFD7EGfhmAvwSVfYzQ/viewform"}, "style": "secondary","color": "#ee9382", "margin": "md"},
        {"type": "button", "action": {"type": "message", "label": "院務會議請假", "text": "院務會議請假"}, "style": "secondary","color": "#ee9382", "margin": "md"},
        {"type": "button", "action": {"type": "message", "label": "夜點費申請", "text": "夜點費申請"}, "style": "secondary","color": "#ee9382", "margin": "md"},
        {"type": "button", "action": {"type": "message", "label": "加班申請", "text": "加班申請"}, "style": "primary","color": "#ee9382", "margin": "md"},
        {"type": "button", "action": {"type": "message", "label": "醫師資訊查詢（限制使用）", "text": "查詢醫師資料（限制使用）"}, "style": "primary", "color": "#4B89DC", "margin": "md"}
    ]
}








# ✅ 主訊息處理
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    source_type = event.source.type         # 'user', 'group', 'room'
    raw_text = event.message.text.strip()   # 使用者原始輸入
    text = get_event_text(event)            # 經處理後的指令文字（按鈕文字也會轉換）





    
    # ✅ 群組訊息過濾器：只允許統計指令，其餘全部略過
    if source_type != "user" and not is_stat_trigger(text):
        print(f"❌ 忽略群組非統計訊息：{text}")
        return

    # ✅ 顯示群組 ID：輸入 [顯示ID] 即回傳
    if text == "[顯示ID]":
        if source_type == "group":
            group_id = event.source.group_id
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(
                    text=f"✅ 群組 ID：\n{group_id}\n\n👉 可貼入 .env：\nMY_GROUP_ID={group_id}"
                )
            )
        else:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="⚠️ 請在群組中輸入 [顯示ID]，我才會回傳群組 ID")
            )
        return

    # ✅ 從 Google Sheet 對照表取得真實使用者名稱（群組也可）
    from utils.google_sheets import get_doctor_name, DOCTOR_SHEET_URL
    user_name = get_doctor_name(DOCTOR_SHEET_URL, user_id) or "未知使用者"

    # ✅ 處理統計功能（支援群組與私訊）
    if handle_stats(event, user_id, text, line_bot_api, user_name):
        return




    # ✅ 每次進來都補 userId（一定要）
    ensure_user_id_exists(user_id)
    
    # ✅ 嘗試處理綁定流程（若正在進行中）
    reply = handle_user_binding(event, line_bot_api)
    if reply:
        line_bot_api.reply_message(event.reply_token, reply)
        return
    


    # ✅ 處理群組投票功能（允許群組進行）
    if handle_group_vote(event, line_bot_api):
        return


    # ✅ 醫師資訊查詢（限制使用）
    if handle_doctor_query(event, line_bot_api, user_id, text):
        return

    # ✅ 加班申請流程
    if handle_overtime(event, user_id, text, line_bot_api):
        return




    
    
    # ✅ 主選單
    if text == "主選單":
        line_bot_api.reply_message(event.reply_token, main_menu_v2_bubble())
        return

    # ✅ 子選單
    if text in submenu_map:
        submenu = submenu_map[text]
    
        bubble = {
            "type": "bubble",
            "size": "mega",
            "body": {
                "type": "box",
                "layout": "vertical",
                "spacing": "md",
                "backgroundColor": "#FFFFFF",  # ✅ 白底（可改為 #FFFFFF80 做透明）
                "contents": [
                    {
                        "type": "text",
                        "text": f"📂 {text}",
                        "weight": "bold",
                        "size": "xl",
                        "color": "#222222",
                        "margin": "md"
                    }
                ] + submenu
            }
        }
    
        line_bot_api.reply_message(
            event.reply_token,
            FlexSendMessage(alt_text=text, contents=bubble)
        )
        return




    # ✅ 處理其他功能（只開放私訊）
    if source_type == "user":
        if handle_duty_message(event, user_id, text, line_bot_api): return
        if handle_meeting_leave(event, user_id, text, line_bot_api): return
        if handle_night_fee(event, user_id, text, line_bot_api): return
        if handle_support_adjustment(event, user_id, text, line_bot_api): return
        if handle_adjustment(event, user_id, text, line_bot_api): return
        return

    
@handler.add(PostbackEvent)
def handle_postback(event):
    user_id = event.source.user_id
    if event.postback.data == "confirm_overtime":
        from handlers.overtime_handler import submit_overtime
        submit_overtime(user_id, line_bot_api, event.reply_token)
    elif event.postback.data == "cancel_overtime":
        from utils.session_manager import clear_session
        clear_session(user_id)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="❌ 已取消加班申請"))




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







#✅ 院務會議請假表單提交
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


#✅ 支援醫師呼叫
@handler.add(PostbackEvent)
def handle_postback(event):
    user_id = event.source.user_id
    data = event.postback.data

    if data == "confirm_support":
        from handlers.support_adjust_handler import submit_support_adjustment
        submit_support_adjustment(user_id, line_bot_api, event.reply_token)
    elif data == "cancel_support":
        from utils.session_manager import clear_session
        clear_session(user_id)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="❌ 已取消申請"))







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


# ✅ 加班申請
@app.route('/api/overtime', methods=['POST'])
def api_overtime():
    try:
        SERVICE_ACCOUNT_JSON = os.environ.get('GOOGLE_CREDENTIALS')
        data = request.get_json()
        name = data.get('name')
        date = data.get('date')
        time_range = data.get('time')
        reason = data.get('reason')

        if not name or not date or not time_range or not reason:
            return jsonify({"error": "缺少必要欄位"}), 400

        # ✅ 取得 Google Sheets 服務
        info = json.loads(SERVICE_ACCOUNT_JSON)
        creds = service_account.Credentials.from_service_account_info(
            info,
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        service = build('sheets', 'v4', credentials=creds)
        sheet = service.spreadsheets()

        # ✅ 寫入 Google Sheets
        sheet.values().append(
            spreadsheetId="1pb5calRrKlCWx16XENcit85pF0qLoH1lvMfGI_WZ_n8",  # 你的加班申請表
            range="加班申請!A:E",
            valueInputOption="RAW",
            body={
                "values": [[
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    data.get('dept', ''),  # ✅ 醫師科別
                    name,
                    date,
                    time_range,
                    reason
                ]]
            }
        ).execute()

        return jsonify({"message": "✅ 加班申請已送出"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500




# ✅ 啟動 Flask 伺服器
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # 預設 port 5000
    print(f"✅ Flask app starting on port {port}")
    app.run(host="0.0.0.0", port=port)


