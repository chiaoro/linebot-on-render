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
import re
from meeting_reminder import send_meeting_reminder
from monthly_reminder import send_monthly_fixed_reminders
from event_reminder import send_important_event_reminder




#✅ 各群組的投票記錄與統計開關
user_votes = {}
stat_active = {}  # 紀錄哪些群組開啟了統計功能
user_sessions = {}


# ✅ 環境設定與 Flask 啟動
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


DOCTOR_SHEET_URL = "https://docs.google.com/spreadsheets/d/1fHf5XlbvLMd6ytAh_t8Bsi5ghToiQHZy1NlVfEG7VIo/edit"
RECORD_SHEET_URL = "https://docs.google.com/spreadsheets/d/1-mI71sC7TE-f8Gb9YPddhVGJrozKxLIdJlSBf2khJsA/edit"
spreadsheet = gc.open_by_key("1fHf5XlbvLMd6ytAh_t8Bsi5ghToiQHZy1NlVfEG7VIo")
mapping_sheet = spreadsheet.worksheet("UserMapping")

user_sessions = {}

# ✅ Flex Menu 設定
def get_main_menu():
    return FlexSendMessage("主選單", {
        "type": "bubble",
        "body": {
            "type": "box", "layout": "vertical", "contents": [
                {"type": "text", "text": "📋 請選擇服務類別", "weight": "bold", "size": "lg", "margin": "md"},
                *[
                    {"type": "button", "action": {"type": "message", "label": label, "text": label},
                     "style": "primary", "margin": "md"}
                    for label in ["門診調整服務","值班調整服務", "支援醫師服務", "新進醫師服務", "其他表單服務"]
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

clinic_buttons = [{"type": "button", "action": {"type": "message", "label": txt, "text": txt}, "style": "primary", "margin": "md"} for txt in ["我要調診", "我要休診", "我要代診", "我要加診"]]+ [
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
    {"type": "button", "action": {"type": "uri", "label": "在職證明申請表", "uri": "https://docs.google.com/forms/d/e/1FAIpQLSeI64Av1Fb2Qgm6lCwTaUyvFRejHItS5KTQNujs1rU3NufMEA/viewform?usp=header"}, "style": "secondary", "margin": "md"},
    {"type": "button", "action": {"type": "uri", "label": "外科醫師休假登記表", "uri": "https://docs.google.com/forms/d/e/1FAIpQLScT2xDChXI7jBVPAf0rzKmtTXXtbZ6JFFD7EGfhmAvwSVfYzQ/viewform"}, "style": "secondary", "margin": "md"},
    {"type": "button", "action": {"type": "message", "label": "院務會議請假", "text": "院務會議請假"}, "style": "secondary", "margin": "md"}
]
duty_swap_buttons = [
    {"type": "button", "action": {"type": "message", "label": "值班調換（互換）", "text": "值班調換"}, "style": "primary", "margin": "md"},
    {"type": "button", "action": {"type": "message", "label": "值班代理", "text": "值班代理"}, "style": "primary", "margin": "md"}
]





@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    user_msg = event.message.text.strip()
    global user_votes, stat_active

    # 統一處理訊息，去除中括號與空白（避免格式不一致）
    text = user_msg.replace("【", "").replace("】", "").strip()



#    # ✅取得群組ID   -----判斷是不是群組訊息
#    if event.source.type == "group":
#        group_id = event.source.group_id
#        user_id = event.source.user_id
#        print(f"[DEBUG] 群組ID：{group_id}，發話者ID：{user_id}")

#        line_bot_api.reply_message(
#            event.reply_token,
#            TextSendMessage(text=f"群組 ID 為：\n{group_id}")
#        )













    
    

    # ✅ 統計功能 - 僅處理群組中的訊息
    if event.source.type == "group":
        group_id = event.source.group_id
        if group_id not in user_votes:
            user_votes[group_id] = {}
            stat_active[group_id] = False

        if text == "開啟統計":
            user_votes[group_id] = {}
            stat_active[group_id] = True
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="🟢 統計功能已開啟！請大家踴躍 +1 ～如果臨時要取消請喊 -1 ～"))
            return

        if text == "結束統計":
            if stat_active[group_id]:
                total = sum(user_votes[group_id].values())
                stat_active[group_id] = False
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"🔴 統計已結束，總人數為：{total} 人 🙌"))
            else:
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="⚠️ 尚未開啟統計功能。"))
            return

        if text == "統計人數":
            if stat_active[group_id]:
                total = sum(user_votes[group_id].values())
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"📊 統計進行中，目前為 {total} 人。"))
            else:
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="⚠️ 尚未開啟統計功能。"))
            return

        if stat_active[group_id]:
                # ➕ 捕捉 +1 ~ +99 等加票
            plus_match = re.match(r"^\+(\d+)$", text)
            if plus_match:
                count = int(plus_match.group(1))
                user_votes[group_id][len(user_votes[group_id])] = count
                return
              # ➖ 撤銷最後一筆
            elif text == "-1":
                if user_votes[group_id]:
                    user_votes[group_id].popitem()
                return












     # ✅主選單叫出來
    if user_msg == "主選單":
        line_bot_api.reply_message(event.reply_token, get_main_menu())
        return

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
     # ✅主選單







    

    
# ✅ 支援醫師調診單流程（四步驟）
    if user_msg == "支援醫師調診單":
        user_sessions[user_id] = {"step": 0, "type": "支援醫師調診單"}
        line_bot_api.reply_message(
            event.reply_token, 
            TextSendMessage(text="👨‍⚕️ 請問需異動門診醫師姓名？")
        )
        return
    
    if user_id in user_sessions and user_sessions[user_id].get("type") == "支援醫師調診單":
        session = user_sessions[user_id]
    
        if session["step"] == 0:
            session["doctor_name"] = user_msg
            session["step"] = 1
            line_bot_api.reply_message(
                event.reply_token, 
                TextSendMessage(text="📅 請問原本門診是哪一天？（例如：5/6 上午診）")
            )
    
        elif session["step"] == 1:
            session["original_date"] = user_msg
            session["step"] = 2
            line_bot_api.reply_message(
                event.reply_token, 
                TextSendMessage(text="⚙️ 請問您希望如何處理？（例如：休診、調整至5/16 上午診）")
            )
    
        elif session["step"] == 2:
            session["new_date"] = user_msg
            session["step"] = 3
            line_bot_api.reply_message(
                event.reply_token, 
                TextSendMessage(text="📝 最後，請輸入原因（例如：需返台、會議）")
            )
    
        elif session["step"] == 3:
            session["reason"] = user_msg
    
            webhook_url = "https://script.google.com/macros/s/AKfycbwLGVRboA0UDU_HluzYURY6Rw4Y8PKMfbclmbWdqpx7MAs37o18dqPkAssU1AuZrC8hxQ/exec"
            payload = {
                "user_id": user_id,
                "request_type": "支援醫師調診單",
                "doctor_name": session["doctor_name"],  # ✅ 用戶輸入的醫師姓名
                "original_date": session["original_date"],
                "new_date": session["new_date"],
                "reason": session["reason"]
            }
    
            print("📤 準備送出 payload：", payload)
    
            try:
                response = requests.post(
                    webhook_url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                print(f"✅ Webhook status: {response.status_code}")
                print(f"✅ Webhook response: {response.text}")
    
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(
                        text=f"""✅ 已收到您的申請（支援醫師調診單）：
    醫師：{session['doctor_name']}
    原門診：{session['original_date']}
    處理方式：{session['new_date']}
    原因：{session['reason']}"""
                    )
                )
    
            except Exception as e:
                print("❌ webhook 送出失敗：", str(e))
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(
                        text=f"""⚠️ 系統處理失敗，但已記下您的申請：
    醫師：{session['doctor_name']}
    原門診：{session['original_date']}
    處理方式：{session['new_date']}
    原因：{session['reason']}
    請聯繫管理員確認是否成功記錄。"""
                    )
                )
    
            # 清除狀態
            del user_sessions[user_id]
            return





    


    

        
    # ✅ 調診三步驟
    if user_msg in ["我要調診", "我要休診", "我要代診", "我要加診"]:
        user_sessions[user_id] = {"step": 1, "type": user_msg}
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請問原本門診是哪一天？（例如 5/6 上午診）"))
        return

    if user_id in user_sessions and user_sessions[user_id].get("type") in ["我要調診", "我要休診", "我要代診", "我要加診"]:
        session = user_sessions[user_id]
        if session["step"] == 1:
            session["original_date"] = user_msg
            session["step"] = 2
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請問您希望如何處理？例如:(5/23 下午診)(休診)(5/23 下午加診)(XXX代診)"))
        elif session["step"] == 2:
            session["new_date"] = user_msg
            session["step"] = 3
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請問原因是什麼？"))
        elif session["step"] == 3:
            session["reason"] = user_msg
            webhook_url = "https://script.google.com/macros/s/AKfycbwgmpLgjrhwquI54fpK-dIA0z0TxHLEfO2KmaX-meqE7ENNUHmB_ec9GC-7MNHNl1eJ/exec"
            requests.post(webhook_url, json={
                "user_id": user_id,
                "request_type": session["type"],
                "original_date": session["original_date"],
                "new_date": session["new_date"],
                "reason": session["reason"]
            })
            line_bot_api.reply_message(event.reply_token, TextSendMessage(
                text=f"""✅ 已收到您的申請：\n申請類型：{session['type']}\n原門診：{session['original_date']}\n處理方式：{session['new_date']}\n原因：{session['reason']}"""
            ))
            del user_sessions[user_id]
        return



    # ✅ 院務會議請假流程
    if "院務會議" in user_msg:
        set_state(user_id, "ASK_LEAVE")
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請問你這禮拜院務會議是否要請假？請輸入 Y 或 N"))
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









    


    # ✅啟動值班調整流程
    if user_msg == "值班調換":
        user_sessions[user_id] = {"step": 0, "type": "值班調換"}
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="🟡 請問值班班別是？（例如內科急診白班、骨科會診值班）"))
        return

    if user_msg == "值班代理":
        user_sessions[user_id] = {"step": 0, "type": "值班代理"}
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="🟡 請問值班班別是？（例如內科急診白班、骨科會診值班）"))
        return

    # 值班調換與代理處理流程
    if user_id in user_sessions:
        session = user_sessions[user_id]
        step = session["step"]
        swap_type = session["type"]

        if swap_type == "值班調換":
            questions = [
                "🟡 請問原本值班醫師是誰？",
                "🟡 請問原本的值班日期是？（例如5/2 (0800-2000)）",
                "🟡 請問調換值班醫師是誰？",
                "🟡 請問調換的值班日期是？（例如5/3 (0800-2000)）",
                "🟡 請問調換原因是？"
            ]
            key_list = ["班別", "原值班醫師", "原值班日期", "對方醫師", "對方值班日期", "原因"]

        elif swap_type == "值班代理":
            questions = [
                "🟡 請問原本值班醫師是誰？",
                "🟡 請問原本的值班日期是？（例如5/2 (0800-2000)）",
                "🟡 請問代理值班醫師是誰？",
                "🟡 請問代理原因是？"
            ]
            key_list = ["班別", "原值班醫師", "原值班日期", "代理醫師", "原因"]

        if step < len(key_list):
            session[key_list[step]] = user_msg
            session["step"] += 1

            if session["step"] < len(key_list):
                next_question = questions[session["step"] - 1]
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text=next_question))
            else:
                # 組裝資料送出至 Google Apps Script Webhook
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="📨 資料提交中，請稍候..."))

                data = {
                    "swap_type": swap_type,
                    **{k: session.get(k, "") for k in key_list}
                }

                try:
                    webhook_url = "https://script.google.com/macros/s/AKfycbxonJeiBfqvPQnPyApWAc_3B8mwvC9b1lA6B4E_rQLIULdPzifcAYzYH5c1PrWdEHl1Tw/exec"
                    requests.post(webhook_url, data=data)
                    confirm = "\n".join([f"{k}：{data[k]}" for k in key_list])
                    line_bot_api.push_message(user_id, TextSendMessage(text=f"✅ 值班{swap_type}資料已提交成功：\n{confirm}"))
                except Exception as e:
                    line_bot_api.push_message(user_id, TextSendMessage(text=f"❌ 發送失敗：{str(e)}"))

                user_sessions.pop(user_id)
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


#✅院務會議請假申請推播
@app.route("/reminder", methods=["GET"])
def reminder():
    from meeting_reminder import send_meeting_reminder
    send_meeting_reminder(gspread_client)
    return "提醒已送出", 200

#✅固定日期推播
@app.route("/monthly-reminder", methods=["GET"])
def monthly_reminder():
    send_monthly_fixed_reminders()
    return "固定日期推播完成", 200

#✅重要會議推播
@app.route("/event-reminder", methods=["GET"])
def event_reminder():
    send_important_event_reminder()
    return "重要會議提醒完成", 200


# ✅ 喚醒用的 ping 路由
@app.route("/ping", methods=["GET"])
def ping():
    return "Bot is awake!", 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"✅ Flask app starting on port {port}")
    app.run(host="0.0.0.0", port=port)
