# ✅ 主程式，整合所有功能（院務會議 Flex + 夜點費 + 各申請流程 + 自動排程）

from flask import Flask, request, abort, jsonify
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import TextMessage, MessageEvent, TextSendMessage, FlexSendMessage
import os, json, gspread, re, requests
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv

# ✅ 自訂的模組
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
from utils.night_shift_fee import handle_night_shift_request, continue_night_shift_fee_request


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



# ✅ 主選單 Flex
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

# ✅ 子選單 Flex
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





# ✅ 訊息處理
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    user_msg = event.message.text.strip()
    text = user_msg.replace("【", "").replace("】", "").strip()



        # ✅ 夜點費申請流程
    reply = handle_night_shift_request(user_id, user_msg)
    if reply:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
        return

    reply = continue_night_shift_fee_request(user_id, user_msg)
    if reply:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
        return


    # ✅ 院務會議請假 FLEX 流程
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
                        {"type": "text", "text": "📋 院務會議請假", "weight": "bold", "size": "xl", "align": "center"},
                        {"type": "text", "text": "請問您是否出席院務會議？", "wrap": True, "align": "center"},
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
        )
        line_bot_api.reply_message(event.reply_token, flex_message)
        return

    # ✅ 夜點費申請（入口）
    if user_msg == "夜點費申請":
        from utils.night_shift_fee import start_night_shift_fee_request
        reply = start_night_shift_fee_request(user_id)
        if reply:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
        return

    # ✅ 主選單叫出來
    if user_msg == "主選單":
        line_bot_api.reply_message(event.reply_token, get_main_menu())
        return

    # ✅ 子選單叫出來
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

    # ✅ （這裡後面接各種申請流程，如 調診/值班調整/統計功能）




    # ✅ 調診、休診、代診、加診申請（三步驟）
    if user_msg in ["我要調診", "我要休診", "我要代診", "我要加診"]:
        user_sessions[user_id] = {"step": 1, "type": user_msg}
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="📅 請問原本門診是哪一天？（例如 5/6 上午診）"))
        return

    if user_id in user_sessions and user_sessions[user_id].get("type") in ["我要調診", "我要休診", "我要代診", "我要加診"]:
        session = user_sessions[user_id]
        if session["step"] == 1:
            session["original_date"] = user_msg
            session["step"] = 2
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="⚙️ 請問希望如何處理？（如：休診、加診、代診）"))
            return
        elif session["step"] == 2:
            session["new_date"] = user_msg
            session["step"] = 3
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="📝 請問原因是？"))
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
                text=f"""✅ 已收到您的申請：
類型：{session['type']}
原門診：{session['original_date']}
處理方式：{session['new_date']}
原因：{session['reason']}"""
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
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="⚙️ 請問希望如何處理？"))
            return
        elif session["step"] == 2:
            session["new_date"] = user_msg
            session["step"] = 3
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="📝 請問原因？"))
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
                text=f"""✅ 支援醫師調診單已送出：
醫師：{session['doctor_name']}
原門診：{session['original_date']}
新安排：{session['new_date']}
原因：{session['reason']}"""
            ))
            del user_sessions[user_id]
            return

    # ✅ 夜點費申請（正式版）
    from utils.night_shift_fee import continue_night_shift_fee_request
    reply = continue_night_shift_fee_request(user_id, user_msg)
    if reply:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
        return





    # ✅ 值班調整（值班調換 / 值班代理）
    if user_msg in ["值班調換", "值班代理"]:
        user_sessions[user_id] = {"step": 0, "type": user_msg}
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="🟡 請問值班班別是？（例如：內科急診白班）"))
        return

    if user_id in user_sessions and user_sessions[user_id].get("type") in ["值班調換", "值班代理"]:
        session = user_sessions[user_id]
        swap_type = session["type"]
        step = session["step"]

        questions_swap = [
            "🟡 請問原本值班醫師是誰？",
            "📅 原值班日期是？（例如5/2 (0800-2000)）",
            "🔁 調換值班醫師是誰？",
            "📅 調換後的值班日期？",
            "📝 調整原因是？"
        ]
        questions_proxy = [
            "🟡 請問原本值班醫師是誰？",
            "📅 原值班日期是？（例如5/2 (0800-2000)）",
            "👥 代理值班醫師是誰？",
            "📝 代理原因是？"
        ]

        questions = questions_swap if swap_type == "值班調換" else questions_proxy

        if step < len(questions):
            session[f"answer_{step}"] = user_msg
            session["step"] += 1
            if session["step"] < len(questions):
                next_question = questions[session["step"]]
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text=next_question))
            else:
                # ✅ 資料收集完畢，送出到 webhook
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="📨 資料提交中，請稍候..."))

                data = {
                    "swap_type": swap_type,
                    "班別": session.get("answer_0", ""),
                    "原值班醫師": session.get("answer_1", ""),
                    "原值班日期": session.get("answer_2", ""),
                }

                if swap_type == "值班調換":
                    data.update({
                        "對方醫師": session.get("answer_3", ""),
                        "對方值班日期": session.get("answer_4", ""),
                        "原因": session.get("answer_5", "")
                    })
                else:
                    data.update({
                        "代理醫師": session.get("answer_3", ""),
                        "原因": session.get("answer_4", "")
                    })

                webhook_url = "https://script.google.com/macros/s/你的值班調整webhook/exec"
                requests.post(webhook_url, data=data)

                line_bot_api.push_message(user_id, TextSendMessage(text="✅ 已成功提交值班調整申請！"))
                del user_sessions[user_id]
        return

    # ✅ 群組統計功能
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
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"🔄 已切換主題為「{topic}」"))
            return

        if text == "結束統計":
            topic = stat_active.get(group_id)
            if topic:
                total = sum(user_votes[group_id][topic].values())
                stat_active[group_id] = None
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"🔴 統計「{topic}」結束！總人數：{total}"))
            return

    # ✅ 全域防呆提示
    if any(word in user_msg for word in ["調診", "加診", "休診", "代診"]) and user_msg not in ["我要調診", "我要休診", "我要代診", "我要加診", "支援醫師調診單"]:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="⚠️ 若要申請門診異動，請從主選單選擇正確項目喔～"))
        return

    if any(word in user_msg for word in ["值班", "調換", "代理"]) and user_msg not in ["值班調換", "值班代理"]:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="⚠️ 若要申請值班調整，請從主選單選擇正確項目喔～"))
        return



# ✅ LINE Webhook 接收器
@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get('X-Line-Signature')
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return "OK"

# ✅ 每日自動檢查是否開啟院務會議請假
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
        return f"❌ 每日推播失敗：{e}", 500

# ✅ 夜點費產出
@app.route("/generate-night-fee-word", methods=["GET"])
def generate_night_fee_word():
    try:
        run_generate_night_fee_word()
        return "✅ 夜點費申請表已成功產出", 200
    except Exception as e:
        return f"❌ 夜點費產出錯誤：{e}", 500

# ✅ 夜點費每日提醒
@app.route("/night-shift-reminder", methods=["GET"])
def night_shift_reminder():
    try:
        daily_night_fee_reminder()
        return "✅ 夜點費提醒完成", 200
    except Exception as e:
        return f"❌ 夜點費提醒失敗：{e}", 500

# ✅ Google 表單送來的休假資料接收
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

# ✅ Bot 喚醒專用（避免 Render 睡死）
@app.route("/ping", methods=["GET"])
def ping():
    return "Bot is awake!", 200

# ✅ 預設首頁
@app.route("/", methods=["GET"])
def home():
    return "LINE Bot is running!"

# ✅ 啟動 Flask App
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"✅ Flask app starting on port {port}")
    app.run(host="0.0.0.0", port=port)
