# app.py
from flask import Flask, request, abort, jsonify
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import TextMessage, MessageEvent, TextSendMessage, FlexSendMessage
import os, json, requests
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from dotenv import load_dotenv
import re

# utils imports
from utils.line_push import push_text_to_user
from utils.schedule_utils import handle_submission
from utils.google_auth import get_gspread_client
from utils.google_sheets import log_meeting_reply, get_doctor_name
from utils.state_manager import set_state, get_state, clear_state
from utils.night_shift_fee import handle_night_shift_request, daily_night_fee_reminder
from utils.night_shift_fee_generator import generate_night_fee_word
from utils.meeting_reminder import send_meeting_reminder
from utils.monthly_reminder import send_monthly_fixed_reminders
from utils.event_reminder import send_important_event_reminder
from daily_notifier import run_daily_push


# Global storages
user_votes = {}
stat_active = {}
user_sessions = {}

# Flask & LINE init
load_dotenv()
app = Flask(__name__)
line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))

# Google Sheets init
SCOPE = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
creds_dict = json.loads(os.getenv("GOOGLE_CREDENTIALS","{}"))
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
gc = gspread.authorize(creds)


# Sheets for mapping and stats (set env vars DOCTOR_SHEET_KEY, STATS_SHEET_KEY)
mapping_sheet = gc.open_by_key(os.getenv("DOCTOR_SHEET_KEY")).worksheet("UserMapping")
stats_log_sheet = gc.open_by_key(os.getenv("STATS_SHEET_KEY")).worksheet("統計記錄")

# --- Flex 主選單、子選單定義 ---

main_menu_labels = ["門診調整服務", "值班調整服務", "支援醫師服務", "新進醫師服務", "其他表單服務"]

clinic_buttons = [
    {"type": "button", "action": {"type": "message", "label": txt, "text": txt}, "style": "primary", "margin": "md"}
    for txt in ["我要調診", "我要休診", "我要代診", "我要加診"]
] + [
    {"type": "button", "action": {"type": "message", "label": "值班調整服務", "text": "值班調整服務"}, "style": "secondary", "margin": "md"}
]

duty_buttons = [
    {"type": "button", "action": {"type": "message", "label": "值班調換", "text": "值班調換"}, "style": "primary", "margin": "md"},
    {"type": "button", "action": {"type": "message", "label": "值班代理", "text": "值班代理"}, "style": "primary", "margin": "md"}
]

support_buttons = [
    {"type": "button", "action": {"type": "uri", "label": "必填資料", "uri": "https://docs.google.com/forms/d/e/1FAIpQLSe0uYZEF2-bBY14_nKlykFuV__CEeEeOaGVrQJiai9cVoZWLQ/viewform"}, "style": "secondary", "margin": "md"},
    {"type": "button", "action": {"type": "message", "label": "支援醫師調診單", "text": "支援醫師調診單"}, "style": "primary", "margin": "md"}
]

newcomer_buttons = [
    {"type": "button", "action": {"type": "uri", "label": "必填資料", "uri": "https://docs.google.com/forms/d/e/1FAIpQLScUn1Bm83wZ7SSTYCl8fj7z3b_sq7tscrZiXSt_AXOHf0SKPw/viewform"}, "style": "secondary", "margin": "md"},
    {"type": "button", "action": {"type": "uri", "label": "新進須知", "uri": "https://docs.google.com/forms/d/e/1FAIpQLSfH7139NRH2SbV8BjRBioXHtD_6KLMYtfmktJxEBxUc7OW3Kg/viewform"}, "style": "secondary", "margin": "md"}
]

other_buttons = [
    {"type": "button", "action": {"type": "uri", "label": "Temp傳檔", "uri": "https://docs.google.com/forms/d/e/1FAIpQLSexoPBHmJYpBlz_IIsSIO2GIB74dOR2FKPu7FIKjAmKIAqOcw/viewform"}, "style": "secondary", "margin": "md"},
    {"type": "button", "action": {"type": "uri", "label": "專師每日服務量填寫", "uri": "https://forms.office.com/Pages/ResponsePage.aspx?id=qul4xIkgo06YEwYZ5A7JD8YDS5UtAC5Gqgno_TUvnw1UQk1XR0MyTzVRNFZIOTcxVVFRSFdIMkQ1Ti4u"}, "style": "secondary", "margin": "md"},
    {"type": "button", "action": {"type": "uri", "label": "在職證明申請", "uri": "https://docs.google.com/forms/d/e/1FAIpQLSeI64Av1Fb2Qgm6lCwTaUyvFRejHItS5KTQNujs1rU3NufMEA/viewform"}, "style": "secondary", "margin": "md"},
    {"type": "button", "action": {"type": "uri", "label": "外科醫師休假登記表", "uri": "https://docs.google.com/forms/d/e/1FAIpQLScT2xDChXI7jBVPAf0rzKmtTXXtbZ6JFFD7EGfhmAvwSVfYzQ/viewform"}, "style": "secondary", "margin": "md"},
    {"type": "button", "action": {"type": "message", "label": "院務會議請假", "text": "院務會議請假"}, "style": "secondary", "margin": "md"},
    {"type": "button", "action": {"type": "message", "label": "夜點費申請", "text": "夜點費申請"}, "style": "secondary", "margin": "md"}
]

submenu_map = {
    "門診調整服務": clinic_buttons,
    "值班調整服務": duty_buttons,
    "支援醫師服務": support_buttons,
    "新進醫師服務": newcomer_buttons,
    "其他表單服務": other_buttons
}

def get_main_menu():
    return FlexSendMessage("主選單", {
        "type": "bubble",
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {"type": "text", "text": "📋 請選擇服務類別", "weight": "bold", "size": "lg"}
            ] + [
                {"type": "button", "action": {"type": "message", "label": label, "text": label}, "style": "primary", "margin": "md"}
                for label in main_menu_labels
            ]
        }
    })

def get_submenu(title, buttons):
    return FlexSendMessage(title, {
        "type": "bubble",
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {"type": "text", "text": f"📂 {title}", "weight": "bold", "size": "lg"}
            ] + buttons
        }
    })


meeting_flex = {"type":"bubble","size":"mega","body":{"type":"box","layout":"vertical","spacing":"md","contents":[
    {"type":"text","text":"📋 院務會議請假","weight":"bold","size":"xl","align":"center"},
    {"type":"text","text":"請問您是否出席？","wrap":True,"align":"center"},
    {"type":"box","layout":"horizontal","spacing":"md","contents":[
        {"type":"button","style":"primary","action":{"type":"message","label":"✅ 出席","text":"✅ 出席"}},
        {"type":"button","style":"primary","color":"#FF6666","action":{"type":"message","label":"❌ 請假","text":"❌ 請假"}}
    ]}
]}}

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    text = event.message.text.strip()

    # ✅ 夜點費申請流程
    reply = handle_night_shift_request(text)
    if reply:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
        return

    # ✅ 群組統計流程（只在 group 群組內）
    if event.source.type == "group":
        gid = event.source.group_id
        user_votes.setdefault(gid, {})
        stat_active.setdefault(gid, None)

        # 開啟統計
        if text.startswith("開啟統計："):
            topic = text.replace("開啟統計：", "").strip()
            user_votes[gid][topic] = {}
            stat_active[gid] = topic
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"🟢 統計主題「{topic}」已啟動，請大家+1"))
            return

        # 切換主題
        if text.startswith("切換主題："):
            topic = text.replace("切換主題：", "").strip()
            if topic in user_votes[gid]:
                stat_active[gid] = topic
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"🔄 切換至主題「{topic}」"))
            else:
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="⚠️ 查無此主題"))
            return

        # 結束統計
        if text == "結束統計":
            topic = stat_active.get(gid)
            if topic and topic in user_votes[gid]:
                total = sum(user_votes[gid][topic].values())
                stat_active[gid] = None
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                stats_log_sheet.append_row([now, gid, topic, total])
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"🔴 統計「{topic}」結束，總人數：{total}人"))
            else:
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="⚠️ 尚未開啟統計主題"))
            return

    # ✅ 防呆提示（避免錯選）
    if any(w in text for w in ["調診", "加診", "休診", "代診"]) and text not in ["我要調診", "我要休診", "我要代診", "我要加診"]:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="⚠️ 請從主選單選擇對應申請功能。"))
        return
    if any(w in text for w in ["值班", "調換", "代理"]) and text not in ["值班調換", "值班代理"]:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="⚠️ 請從主選單選擇對應申請功能。"))
        return

    # ✅ Flex 主選單
    if text == "主選單":
        line_bot_api.reply_message(event.reply_token, get_main_menu())
        return

    # ✅ Flex 子選單
    if text in submenu_map:
        line_bot_api.reply_message(event.reply_token, get_submenu(text, submenu_map[text]))
        return

    # ✅ 院務會議請假 Flex
    if text == "院務會議請假":
        meeting_flex = {
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
        line_bot_api.reply_message(event.reply_token, FlexSendMessage("院務會議請假", meeting_flex))
        return

    # ✅ 預設提示
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text="⚠️ 無效指令，請輸入「主選單」重新開始。"))






# ✅ LINE官方callback處理
@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature")
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK", 200

# ✅ Google表單submit資料處理（外科醫師休假用）
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

# ✅ 預設首頁
@app.route("/", methods=["GET"])
def home():
    return "LINE Bot is running", 200

# ✅ 院務會議請假推播
@app.route("/meeting-reminder", methods=["GET"])
def meeting_reminder_route():
    send_meeting_reminder()
    return "✅ 會議提醒完成", 200

# ✅ 固定日期推播
@app.route("/monthly-reminder", methods=["GET"])
def monthly_reminder_route():
    send_monthly_fixed_reminders()
    return "✅ 固定日期推播完成", 200

# ✅ 重要會議推播
@app.route("/event-reminder", methods=["GET"])
def event_reminder_route():
    send_important_event_reminder()
    return "✅ 重要會議提醒完成", 200

# ✅ 每日個人推播
@app.route("/daily-push", methods=["GET"])
def daily_push_route():
    run_daily_push()
    return "✅ 今日推播完成", 200

# ✅ 夜點費產生Word文件
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
        from utils.night_shift_fee_reminder import daily_night_fee_reminder
        daily_night_fee_reminder()
        return "✅ 夜點費每日提醒完成", 200
    except Exception as e:
        return f"❌ 夜點費提醒錯誤：{e}", 500

# ✅ 喚醒機制（避免Render睡死）
@app.route("/ping", methods=["GET"])
def ping():
    return "Bot is awake!", 200



if __name__ == "__main__":
    port = int(os.getenv("PORT",5000))
    app.run(host="0.0.0.0", port=port)
