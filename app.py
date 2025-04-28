# app.py
# ✅ 主程式，整合院務會議請假 Flex + 值班調整 + 夜點費 + 自動排程

from flask import Flask, request, abort, jsonify
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import TextMessage, MessageEvent, FlexSendMessage
import os, json, gspread, re, requests
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv

# ✅ 自己的模組
from utils.line_push import push_text_to_user
from utils.schedule_utils import handle_submission
from utils.google_auth import get_gspread_client
from utils.google_sheets import log_meeting_reply, get_doctor_name
from utils.state_manager import set_state, get_state, clear_state
from meeting_reminder import send_meeting_reminder
from monthly_reminder import send_monthly_fixed_reminders
from event_reminder import send_important_event_reminder
from daily_notifier import run_daily_push
from utils.night_shift_fee import handle_night_shift_request, daily_night_fee_reminder
from utils.night_shift_fee_generator import run_generate_night_fee_word
from meeting_leave import handle_meeting_leave_response
from meeting_leave_scheduler import run_meeting_leave_scheduler

# ✅ 環境設定
load_dotenv()
app = Flask(__name__)
line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))

# ✅ Google Sheets 認證
SCOPE = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds_dict = json.loads(os.getenv("GOOGLE_CREDENTIALS"))
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
gc = gspread.authorize(creds)

# ✅ 全域變數
user_sessions = {}
user_votes = {}
stat_active = {}

# ✅ 你的 Sheet URL
DOCTOR_SHEET_URL = "https://docs.google.com/spreadsheets/d/1fHf5XlbvLMd6ytAh_t8Bsi5ghToiQHZy1NlVfEG7VIo/edit"
RECORD_SHEET_URL = "https://docs.google.com/spreadsheets/d/1-mI71sC7TE-f8Gb9YPddhVGJrozKxLIdJlSBf2khJsA/edit"

# ✅ Flex主選單
def get_main_menu():
    return FlexSendMessage("主選單", {
        "type": "bubble",
        "body": {
            "type": "box", "layout": "vertical",
            "contents": [
                {"type": "text", "text": "📋 請選擇服務類別", "weight": "bold", "size": "lg"},
                *[
                    {"type": "button", "action": {"type": "message", "label": label, "text": label}, "style": "primary", "margin": "md"}
                    for label in ["門診調整服務", "值班調整服務", "支援醫師服務", "新進醫師服務", "其他表單服務"]
                ]
            ]
        }
    })



# ✅ 子選單
def get_submenu(title, buttons):
    return FlexSendMessage(title, {
        "type": "bubble",
        "body": {
            "type": "box", "layout": "vertical",
            "contents": [
                {"type": "text", "text": f"📂 {title}", "weight": "bold", "size": "lg"},
                *buttons
            ]
        }
    })

# ✅ 子選單按鈕們
clinic_buttons = [
    {"type": "button", "action": {"type": "message", "label": txt, "text": txt}, "style": "primary", "margin": "md"}
    for txt in ["我要調診", "我要休診", "我要代診", "我要加診"]
] + [
    {"type": "button", "action": {"type": "message", "label": "值班調整服務", "text": "值班調整服務"}, "style": "secondary", "margin": "md"}
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
    {"type": "button", "action": {"type": "uri", "label": "在職證明申請表", "uri": "https://docs.google.com/forms/d/e/1FAIpQLSeI64Av1Fb2Qgm6lCwTaUyvFRejHItS5KTQNujs1rU3NufMEA/viewform"}, "style": "secondary", "margin": "md"},
    {"type": "button", "action": {"type": "uri", "label": "外科醫師休假登記表", "uri": "https://docs.google.com/forms/d/e/1FAIpQLScT2xDChXI7jBVPAf0rzKmtTXXtbZ6JFFD7EGfhmAvwSVfYzQ/viewform"}, "style": "secondary", "margin": "md"},
    {"type": "button", "action": {"type": "message", "label": "院務會議請假", "text": "院務會議請假"}, "style": "secondary", "margin": "md"},
    {"type": "button", "action": {"type": "message", "label": "夜點費申請", "text": "夜點費申請"}, "style": "secondary", "margin": "md"}
]

duty_swap_buttons = [
    {"type": "button", "action": {"type": "message", "label": "值班調換（互換）", "text": "值班調換"}, "style": "primary", "margin": "md"},
    {"type": "button", "action": {"type": "message", "label": "值班代理", "text": "值班代理"}, "style": "primary", "margin": "md"}
]

# ✅ 處理收到的所有訊息
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    user_msg = event.message.text.strip()
    text = user_msg.replace("【", "").replace("】", "").strip()

    # ✅ 院務會議請假
    if handle_meeting_leave_response(event, line_bot_api, user_msg, user_id):
        return

    # ✅ 夜點費申請
    reply = handle_night_shift_request(user_id, user_msg)
    if reply:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
        return

    # ✅ 主選單
    if user_msg == "主選單":
        line_bot_api.reply_message(event.reply_token, get_main_menu())
        return

    # ✅ 子選單
    submenu_map = {
        "門診調整服務": clinic_buttons,
        "值班調整服務": duty_swap_buttons,
        "支援醫師服務": support_buttons,
        "新進醫師服務": newcomer_buttons,
        "其他表單服務": other_buttons
    }
    if user_msg in submenu_map:
        line_bot_api.reply_message(event.reply_token, get_submenu(user_msg, submenu_map[user_msg]))
        return

    # ✅ （這裡後面接各種申請流程）



# ✅ 院務會議請假 - 叫出 Flex
if user_msg == "院務會議請假":
    flex_message = FlexSendMessage(
        alt_text="院務會議請假",
        contents={
            "type": "bubble",
            "size": "mega",
            "body": {
                "type": "box",
                "layout": "vertical",
                "spacing": "md",
                "contents": [
                    {
                        "type": "text",
                        "text": "📋 院務會議請假",
                        "weight": "bold",
                        "size": "xl",
                        "align": "center"
                    },
                    {
                        "type": "text",
                        "text": "請問您是否出席院務會議？",
                        "wrap": True,
                        "align": "center"
                    },
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "spacing": "md",
                        "contents": [
                            {
                                "type": "button",
                                "style": "primary",
                                "action": {
                                    "type": "message",
                                    "label": "✅ 出席",
                                    "text": "✅ 出席"
                                }
                            },
                            {
                                "type": "button",
                                "style": "primary",
                                "color": "#FF6666",
                                "action": {
                                    "type": "message",
                                    "label": "❌ 請假",
                                    "text": "❌ 請假"
                                }
                            }
                        ]
                    }
                ]
            }
        }
    )
    line_bot_api.reply_message(event.reply_token, flex_message)
    return





    # ✅ 調診/休診/代診/加診申請（3步驟）
    if user_msg in ["我要調診", "我要休診", "我要代診", "我要加診"]:
        user_sessions[user_id] = {"step": 1, "type": user_msg}
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請問原本門診是哪一天？（例如 5/6 上午診）"))
        return

    if user_id in user_sessions and user_sessions[user_id].get("type") in ["我要調診", "我要休診", "我要代診", "我要加診"]:
        session = user_sessions[user_id]
        if session["step"] == 1:
            session["original_date"] = user_msg
            session["step"] = 2
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請問您希望如何處理？（例如：休診、5/23下午加診）"))
            return
        elif session["step"] == 2:
            session["new_date"] = user_msg
            session["step"] = 3
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請問原因是什麼？"))
            return
        elif session["step"] == 3:
            session["reason"] = user_msg
            webhook_url = "https://script.google.com/macros/s/你的webhook網址/exec"
            requests.post(webhook_url, json={
                "user_id": user_id,
                "request_type": session["type"],
                "original_date": session["original_date"],
                "new_date": session["new_date"],
                "reason": session["reason"]
            })
            line_bot_api.reply_message(event.reply_token, TextSendMessage(
                text=f"""✅ 已收到您的申請：\n類型：{session['type']}\n原門診：{session['original_date']}\n處理方式：{session['new_date']}\n原因：{session['reason']}"""
            ))
            del user_sessions[user_id]
            return

    # ✅ 支援醫師調診單（四步驟）
    if user_msg == "支援醫師調診單":
        user_sessions[user_id] = {"step": 0, "type": "支援醫師調診單"}
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="👨‍⚕️ 請問需異動門診醫師姓名？"))
        return

    if user_id in user_sessions and user_sessions[user_id].get("type") == "支援醫師調診單":
        session = user_sessions[user_id]
        if session["step"] == 0:
            session["doctor_name"] = user_msg
            session["step"] = 1
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="📅 請問原本門診是哪一天？"))
            return
        elif session["step"] == 1:
            session["original_date"] = user_msg
            session["step"] = 2
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="⚙️ 請問您希望如何處理？"))
            return
        elif session["step"] == 2:
            session["new_date"] = user_msg
            session["step"] = 3
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="📝 最後，請輸入原因"))
            return
        elif session["step"] == 3:
            session["reason"] = user_msg
            webhook_url = "https://script.google.com/macros/s/你的支援醫師webhook/exec"
            requests.post(webhook_url, json={
                "user_id": user_id,
                "request_type": "支援醫師調診單",
                "doctor_name": session["doctor_name"],
                "original_date": session["original_date"],
                "new_date": session["new_date"],
                "reason": session["reason"]
            })
            line_bot_api.reply_message(event.reply_token, TextSendMessage(
                text=f"""✅ 支援醫師調診單送出：
醫師：{session['doctor_name']}
原門診：{session['original_date']}
新安排：{session['new_date']}
原因：{session['reason']}"""
            ))
            del user_sessions[user_id]
            return

    # ✅ 值班調整/代理 流程
    if user_msg in ["值班調換", "值班代理"]:
        user_sessions[user_id] = {"step": 0, "type": user_msg}
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="🟡 請問值班班別是？（例如內科急診白班）"))
        return

    if user_id in user_sessions and user_sessions[user_id].get("type") in ["值班調換", "值班代理"]:
        session = user_sessions[user_id]
        step = session["step"]
        if step == 0:
            session["班別"] = user_msg
            session["step"] = 1
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="🟡 請問原本值班醫師是誰？"))
            return
        elif step == 1:
            session["原值班醫師"] = user_msg
            session["step"] = 2
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="📅 請問原值班日期是？（例如5/2 (0800-2000)）"))
            return
        elif step == 2:
            session["原值班日期"] = user_msg
            if session["type"] == "值班調換":
                session["step"] = 3
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="🔁 請問調換值班醫師是誰？"))
            else:
                session["step"] = 4
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="👥 請問代理值班醫師是誰？"))
            return
        elif step == 3:
            session["對方醫師"] = user_msg
            session["step"] = 4
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="📅 請問調換後的值班日期？"))
            return
        elif step == 4:
            session["對方值班日期" if session["type"] == "值班調換" else "代理醫師"] = user_msg
            session["step"] = 5
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="📝 最後，請輸入調整原因"))
            return
        elif step == 5:
            session["原因"] = user_msg
            webhook_url = "https://script.google.com/macros/s/你的值班調換代理webhook/exec"
            requests.post(webhook_url, data=session)
            line_bot_api.reply_message(event.reply_token, TextSendMessage(
                text="✅ 已送出值班調整單！"
            ))
            del user_sessions[user_id]
            return

    # ✅ 統計功能
    if event.source.type == "group":
        group_id = event.source.group_id
        if group_id not in user_votes:
            user_votes[group_id] = {}
            stat_active[group_id] = None

        if text.startswith("開啟統計："):
            topic = text.replace("開啟統計：", "").strip()
            user_votes[group_id][topic] = {}
            stat_active[group_id] = topic
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"🟢 已開啟統計「{topic}」"))
            return

        if text.startswith("切換主題："):
            topic = text.replace("切換主題：", "").strip()
            if topic in user_votes[group_id]:
                stat_active[group_id] = topic
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"🔄 已切換到主題「{topic}」"))
            return

        if text == "結束統計":
            topic = stat_active.get(group_id)
            if topic:
                total = sum(user_votes[group_id][topic].values())
                stat_active[group_id] = None
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"🔴 統計結束！總人數：{total}"))
            return



# ✅ LINE Webhook 接收器
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature')
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

# ✅ 每天自動檢查是否開啟院務會議請假
@app.route("/daily-check-meeting-leave", methods=["GET"])
def daily_check_meeting_leave():
    try:
        run_meeting_leave_scheduler(line_bot_api)
        return "✅ 每日會議排程檢查完成", 200
    except Exception as e:
        return f"❌ 排程錯誤：{e}", 500

# ✅ 固定日期推播
@app.route("/monthly-reminder", methods=["GET"])
def monthly_reminder():
    send_monthly_fixed_reminders()
    return "✅ 固定日期推播完成", 200

# ✅ 重要會議推播
@app.route("/event-reminder", methods=["GET"])
def event_reminder():
    send_important_event_reminder()
    return "✅ 重要會議推播完成", 200

# ✅ 每日個人推播
@app.route("/daily-push", methods=["GET"])
def daily_push():
    try:
        run_daily_push()
        return "✅ 每日推播完成", 200
    except Exception as e:
        return f"❌ 推播失敗：{e}", 500

# ✅ 產生夜點費申請表
@app.route("/generate-night-fee-word", methods=["GET"])
def generate_night_fee_word():
    try:
        run_generate_night_fee_word()
        return "✅ 夜點費申請表已產出", 200
    except Exception as e:
        return f"❌ 產出錯誤：{e}", 500

# ✅ 夜點費每日提醒
@app.route("/night-shift-reminder", methods=["GET"])
def night_shift_reminder():
    try:
        daily_night_fee_reminder()
        return "✅ 夜點費提醒完成", 200
    except Exception as e:
        return f"❌ 夜點費提醒失敗：{e}", 500

# ✅ 接收 Google 表單送來的休假資料
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

# ✅ 喚醒專用
@app.route("/ping", methods=["GET"])
def ping():
    return "Bot is awake!", 200

# ✅ 測試首頁
@app.route("/", methods=["GET"])
def home():
    return "LINE Bot is running!"

# ✅ 啟動 Flask 主程式
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"✅ Flask app starting on port {port}")
    app.run(host="0.0.0.0", port=port)

