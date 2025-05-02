
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
from utils.meeting_leave_menu import get_meeting_leave_menu
from utils.daily_night_fee_reminder import send_night_fee_reminders
from utils.user_binding import handle_user_binding
from utils.user_binding import send_bind_start_flex, ask_for_name, confirm_binding, ensure_user_id_exists, user_states
from utils.user_binding import ensure_user_id_exists, handle_user_binding
from utils.date_utils import expand_date_range
from utils.group_vote_tracker import handle_group_vote
from utils.bubble_templates import main_menu_v2_bubble
from utils.flex_templates import get_adjustment_bubble, get_duty_swap_bubble
from utils.line_utils import get_event_text, is_trigger




exec(open("utils/night_shift_fee_generator.py", encoding="utf-8").read())

# ✅載入 .env
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
        {"type": "button", "action": {"type": "message", "label": "夜點費申請", "text": "夜點費申請"}, "style": "secondary","color": "#ee9382", "margin": "md"}
    ]
}








# ✅ 主訊息處理
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    text = event.message.text.strip()
    source_type = event.source.type  # 'user', 'group', 'room'



     # ✅ 測ID
     # ✅ 當你在群組輸入 [顯示ID]，回傳群組 ID
    if text == "[顯示ID]":
        if event.source.type == "group":
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














    
    # ✅ Step 1：僅私訊觸發，或特定格式才處理
    trigger_keywords = ["我要調診", "我要休診", "我要代診", "我要加診", "值班調換", "夜點費申請"]

    if source_type != 'user' and not any(text.startswith(k) for k in trigger_keywords):
        print(f"❌ 忽略群組內非關鍵字訊息：{text}")
        return  # 不處理群組內非關鍵字訊息

    # ✅ Step 2：進入你既有的邏輯（例如：「我要調診」流程）
    if text.startswith("我要調診"):
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="請問您希望如何處理？（例如：改5/23 下午診、休診、XXX代診）")
        )
    elif text.startswith("我要休診") or text.startswith("我要代診") or text.startswith("我要加診"):
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="請輸入原因（例如：返台、會議）")
        )
    elif text.startswith("值班調換"):
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="請問是值班【互換】還是【代理】？")
        )

    else:
        # 其他無效格式，也不回應
        print(f"未定義的指令：{text}")





    


    # ✅ 每次進來都補 userId（一定要）
    ensure_user_id_exists(user_id)
    
    # ✅ 嘗試處理綁定流程（若正在進行中）
    reply = handle_user_binding(event, line_bot_api)
    if reply:
        line_bot_api.reply_message(event.reply_token, reply)
        return
    

    # ✅ 處理群組統計功能
    if handle_group_vote(event, line_bot_api):
        return

    


    # ✅ 夜點費申請流程（Flex Bubble + 一步輸入日期 + 自動解析區間）
    if text == "夜點費申請":
        user_sessions[user_id] = {"step": 1, "type": "夜點費申請"}
        bubble = {
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {"type": "text", "text": "🌙 夜點費申請", "weight": "bold", "size": "lg"},
                    {"type": "text", "text": "請輸入值班日期（可輸入區間）", "margin": "md"},
                    {"type": "text", "text": "範例：\n4/10、\n4/15、\n4/17、\n4/18-23", "size": "sm", "color": "#888888", "margin": "md"}
                ]
            }
        }
        flex_msg = FlexSendMessage(alt_text="🌙 夜點費申請", contents=bubble)
        line_bot_api.reply_message(event.reply_token, flex_msg)
        return
    
    
    # ✅ 接收日期並處理
    if user_id in user_sessions and user_sessions[user_id].get("type") == "夜點費申請":
        session = user_sessions[user_id]
        step = session["step"]
    
        if step == 1:
            date_input = text.strip()
            session["step"] = 2
        
            expanded_dates = expand_date_range(date_input)  # 回傳為 list of 字串，如 ["4/25", "4/26"]
        
            # ✅ 正確放入 webhook URL
            webhook_url = "https://script.google.com/macros/s/AKfycbxOKltHGgoz05CKpTJIu4kFdzzmKd9bzL7bT5LOqYu5Lql6iaTlgFI9_lHwqFQFV8-J/exec"
            payload = {
                "user_id": user_id,
                "日期": date_input
            }
        
            try:
                requests.post(webhook_url, json=payload)
                print("📡 webhook 回傳：", response.status_code, response.text)
                
                line_bot_api.reply_message(event.reply_token, TextSendMessage(
                    text=f"""✅ 夜點費資料已送出：
            📆 日期：{date_input}（共 {len(expanded_dates)} 班）"""
                ))
            except Exception as e:
                print("❌ webhook 發送失敗（靜默）：", str(e))
                pass  # 不回應使用者任何訊息
            del user_sessions[user_id]
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




    

    # ✅ 支援醫師調診單（四步驟流程）
    # ✅ 啟動流程（第一句使用 reply_message）
    if text == "支援醫師調診單":
        user_sessions[user_id] = {"step": 0, "type": "支援醫師調診單"}
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="👨‍⚕️ 請問需異動門診醫師姓名？"))
        return
    
    # ✅ 後續全部使用 push_message
    if user_id in user_sessions and user_sessions[user_id].get("type") == "支援醫師調診單":
        session = user_sessions[user_id]
    
        if session["step"] == 0:
            session["doctor_name"] = text
            session["step"] = 1
            line_bot_api.push_message(user_id, TextSendMessage(text="📅 請問原本門診是哪一天？（例如：5/6 上午診）"))
    
        elif session["step"] == 1:
            session["original_date"] = text
            session["step"] = 2
            line_bot_api.push_message(user_id, TextSendMessage(text="⚙️ 請問您希望如何處理？（例如：休診、調整至5/16 上午診）"))
    
        elif session["step"] == 2:
            session["new_date"] = text
            session["step"] = 3
            line_bot_api.push_message(user_id, TextSendMessage(text="📝 最後，請輸入原因（例如：需返台、會議）"))
    
        elif session["step"] == 3:
            session["reason"] = text
            webhook_url = "https://script.google.com/macros/s/AKfycbwLGVRboA0UDU_HluzYURY6Rw4Y8PKMfbclmbWdqpx7MAs37o18dqPkAssU1AuZrC8hxQ/exec"
            payload = {
                "user_id": user_id,
                "request_type": "支援醫師調診單",
                "doctor_name": session["doctor_name"],
                "original_date": session["original_date"],
                "new_date": session["new_date"],
                "reason": session["reason"]
            }
    
            try:
                requests.post(webhook_url, json=payload)
    
                bubble = get_support_adjustment_bubble(
                    doctor_name=session["doctor_name"],
                    original=session["original_date"],
                    method=session["new_date"],
                    reason=session["reason"]
                )
    
                line_bot_api.push_message(
                    user_id,
                    FlexSendMessage(alt_text="支援醫師調診單已送出", contents=bubble)
                )
    
            except Exception as e:
                print("❌ webhook 發送失敗：", str(e))
                line_bot_api.push_message(user_id, TextSendMessage(
                    text="⚠️ 系統提交失敗，請稍後再試或聯絡秘書"
                ))
    
            del user_sessions[user_id]
        return





    

    
    # ✅ 調診/休診/代診/加診（三步驟流程）
    # ✅ 啟動流程（這一句允許使用 reply_token）
    text = get_event_text(event)
    
    if is_trigger(event, ["我要調診", "我要休診", "我要代診", "我要加診"]):
        user_sessions[user_id] = {"step": 0, "type": text}
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="📅 請問原本門診是哪一天？（例如：5/6 上午診）")
        )
        return
    
    # ✅ 後續步驟全改為 push_message（穩定、不會報錯）
    if user_id in user_sessions and user_sessions[user_id].get("type") in ["我要調診", "我要休診", "我要代診", "我要加診"]:
        session = user_sessions[user_id]
    
        if session["step"] == 0:
            session["original_date"] = text
            session["step"] = 1
            line_bot_api.push_message(user_id, TextSendMessage(text="⚙️ 請問您希望如何處理？（例如：改5/23 下午診、休診、XXX代診）"))
    
        elif session["step"] == 1:
            session["new_date"] = text
            session["step"] = 2
            line_bot_api.push_message(user_id, TextSendMessage(text="📝 請輸入原因（例如：返台、會議）"))
    
        elif session["step"] == 2:
            session["reason"] = text
            doctor_name = get_doctor_name(DOCTOR_SHEET_URL, user_id)
            webhook_url = "https://script.google.com/macros/s/AKfycbwgmpLgjrhwquI54fpK-dIA0z0TxHLEfO2KmaX-meqE7ENNUHmB_ec9GC-7MNHNl1eJ/exec"
            payload = {
                "user_id": user_id,
                "request_type": session["type"],
                "original_date": session["original_date"],
                "new_date": session["new_date"],
                "reason": session["reason"],
                "doctor_name": doctor_name
            }
    
            try:
                # ✅ 傳 webhook
                response = requests.post(
                    webhook_url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                print("✅ webhook 回應：", response.status_code, response.text)
    
                # ✅ 推送 Flex Bubble
                bubble = get_adjustment_bubble(
                    original=session["original_date"],
                    method=session["new_date"],
                    reason=session["reason"]
                )
                line_bot_api.push_message(
                    user_id,
                    FlexSendMessage(alt_text="門診調整通知", contents=bubble)
                )
    
            except Exception as e:
                print("❌ webhook 發送失敗：", str(e))
                line_bot_api.push_message(user_id, TextSendMessage(
                    text="⚠️ 系統提交失敗，請稍後再試或聯絡秘書"
                ))
    
            del user_sessions[user_id]
        return







    
    
    # ✅ 值班調換/代理（四～五步驟）
    if text == "值班調換":
        user_sessions[user_id] = {"step": 0, "type": "值班調換"}
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="👨‍⚕️ 請輸入您的姓名"))
        return
    
    if user_id in user_sessions and user_sessions[user_id].get("type") == "值班調換":
        session = user_sessions[user_id]
    
        if session["step"] == 0:
            session["original_doctor"] = text
            session["step"] = 1
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="📅 請輸入原值班班別與日期（例如：夜班 5/10）"))
    
        elif session["step"] == 1:
            # 拆解班別與日期
            try:
                shift_type, date = text.split(" ")
                session["shift_type"] = shift_type
                session["original_date"] = date
            except:
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="⚠️ 請用正確格式輸入，例如：夜班 5/10"))
                return
    
            session["step"] = 2
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="🔁 請輸入對調醫師姓名與調換日期（例如：李大華 5/17）"))
    
        elif session["step"] == 2:
            try:
                name, date = text.split(" ")
                session["target_doctor"] = name
                session["swap_date"] = date
            except:
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="⚠️ 請用正確格式輸入，例如：李大華 5/17"))
                return
    
            session["step"] = 3
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="📝 請輸入調換原因"))
    
        elif session["step"] == 3:
            session["reason"] = text
    
            webhook_url = "https://script.google.com/macros/s/你的_webhook_url/exec"
            payload = {
                "request_type": "值班調換",
                "original_doctor": session["original_doctor"],
                "shift_type": session["shift_type"],
                "original_date": session["original_date"],
                "target_doctor": session["target_doctor"],
                "swap_date": session["swap_date"],
                "reason": session["reason"]
            }
    
            # ✅ 先 reply 表示成功收到
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="📨 已收到申請，稍後會送出調換通知")
            )
    
            try:
                requests.post(webhook_url, json=payload)
    
                bubble = get_duty_swap_bubble(
                    shift_type=session["shift_type"],
                    original_doctor=session["original_doctor"],
                    original_date=session["original_date"],
                    target_doctor=session["target_doctor"],
                    swap_date=session["swap_date"],
                    reason=session["reason"]
                )
    
                line_bot_api.push_message(
                    user_id,
                    FlexSendMessage(alt_text="值班調換通知", contents=bubble)
                )
    
            except Exception as e:
                print("❌ webhook 發送失敗：", str(e))
                line_bot_api.push_message(user_id, TextSendMessage(
                    text="⚠️ 系統提交失敗，請稍後再試"
                ))
    
            del user_sessions[user_id]
        return



    if text == "值班代理":
        user_sessions[user_id] = {"step": 0, "type": "值班代理"}
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="👨‍⚕️ 請輸入您的姓名"))
        return
    
    if user_id in user_sessions and user_sessions[user_id].get("type") == "值班代理":
        session = user_sessions[user_id]
    
        if session["step"] == 0:
            session["original_doctor"] = text
            session["step"] = 1
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="📅 請輸入原值班班別與日期（例如：早班 5/10）"))
    
        elif session["step"] == 1:
            try:
                shift_type, date = text.split(" ")
                session["shift_type"] = shift_type
                session["original_date"] = date
            except:
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="⚠️ 請用正確格式輸入，例如：早班 5/10"))
                return
    
            session["step"] = 2
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="🧑‍⚕️ 請輸入代理醫師姓名"))
    
        elif session["step"] == 2:
            session["proxy_doctor"] = text
            session["step"] = 3
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="📝 請輸入原因"))
    
        elif session["step"] == 3:
            session["reason"] = text
    
            webhook_url = "https://script.google.com/macros/s/你的_webhook_url/exec"
            payload = {
                "request_type": "值班代理",
                "original_doctor": session["original_doctor"],
                "shift_type": session["shift_type"],
                "original_date": session["original_date"],
                "proxy_doctor": session["proxy_doctor"],
                "reason": session["reason"]
            }
    
            # ✅ 先回覆確認文字（防止 reply_token 失效）
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="📨 已收到申請，稍後會送出代理通知")
            )
    
            try:
                requests.post(webhook_url, json=payload)
    
                bubble = get_duty_proxy_bubble(
                    shift_type=session["shift_type"],
                    original_doctor=session["original_doctor"],
                    original_date=session["original_date"],
                    proxy_doctor=session["proxy_doctor"],
                    reason=session["reason"]
                )
    
                line_bot_api.push_message(
                    user_id,
                    FlexSendMessage(alt_text="值班代理通知", contents=bubble)
                )
    
            except Exception as e:
                print("❌ webhook 發送失敗：", str(e))
                line_bot_api.push_message(user_id, TextSendMessage(
                    text="⚠️ 系統提交失敗，請稍後再試"
                ))
    
            del user_sessions[user_id]
        return





    

    

    # ✅ 院務會議請假
    if text == "院務會議請假":
        set_state(user_id, "ASK_LEAVE")
        bubble = {
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "📋 院務會議出席確認",
                        "weight": "bold",
                        "size": "lg",
                        "margin": "md"
                    },
                    {
                        "type": "text",
                        "text": "請問您是否出席本次院務會議？",
                        "size": "sm",
                        "wrap": True,
                        "margin": "md"
                    }
                ]
            },
            "footer": {
                "type": "box",
                "layout": "horizontal",
                "contents": [
                    {
                        "type": "button",
                        "style": "primary",
                        "color": "#9F4D95",  # ✅ 紫色
                        "action": {
                            "type": "message",
                            "label": "✅ 我要出席",
                            "text": "我要出席院務會議"
                        }
                    },
                    {
                        "type": "button",
                        "style": "secondary",
                        "color": "#F4F2F9",  # ❌ 淺紫色
                        "action": {
                            "type": "message",
                            "label": "❌ 我要請假",
                            "text": "我要請假院務會議"
                        }
                    }
                ]
            }
        }
        flex_msg = FlexSendMessage(alt_text="📋 院務會議出席確認", contents=bubble)
        line_bot_api.reply_message(event.reply_token, flex_msg)
        return

    if get_state(user_id) == "ASK_LEAVE":
        if text == "我要出席院務會議":
            doctor_name = get_doctor_name(DOCTOR_SHEET_URL, user_id)
            log_meeting_reply(user_id, "出席", "")
            clear_state(user_id)
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="✅ 已紀錄您出席院務會議。"))
        elif text == "我要請假院務會議":
            set_state(user_id, "ASK_REASON")
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請輸入您無法出席的原因："))
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="⚠️ 請選擇上方按鈕"))
        return

    if get_state(user_id) == "ASK_REASON":
        doctor_name = get_doctor_name(DOCTOR_SHEET_URL, user_id)
        reason = text
        doctor_name, dept = get_doctor_info(DOCTOR_SHEET_URL, user_id)
        log_meeting_reply(user_id, doctor_name, dept, "請假", reason)
        clear_state(user_id)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="✅ 已紀錄您的請假申請。"))
        return









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
        exec(open("utils/night_shift_fee_generator.py", encoding="utf-8").read())
        return "✅ 夜點費申請表產生完成", 200
    except Exception as e:
        return f"❌ 夜點費申請表產生錯誤：{e}", 500





# ✅ 夜點費每日提醒
@app.route("/night-fee-daily-reminder", methods=["GET"])
def night_fee_daily_reminder():
    try:
        send_night_fee_reminders()
        return "✅ 夜點費每日提醒完成", 200
    except Exception as e:
        return f"❌ 夜點費提醒錯誤：{e}", 500




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


# ✅ 夜點費提醒推播（每天早上 7:00）
@app.route("/night-shift-reminder", methods=["GET"])
def night_shift_reminder():
    try:
        from utils.night_shift_fee import run_night_shift_reminder  # 確保函式存在
        run_night_shift_reminder()
        return "✅ 夜點費提醒完成", 200
    except Exception as e:
        return f"❌ night-shift-reminder 錯誤：{e}", 500






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


