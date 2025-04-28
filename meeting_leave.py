# meeting_leave.py
# ✅ 處理單次院務會議出席/請假流程 + 推播請假通知
# by 小秘 GPT

import os
import json
import gspread
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv
from linebot.models import FlexSendMessage, TextSendMessage
from utils.line_push import push_text_to_user
from utils.state_manager import set_state, get_state, clear_state

load_dotenv()

# Google Sheets 認證
SCOPE = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds_dict = json.loads(os.environ.get("GOOGLE_CREDENTIALS"))
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
gc = gspread.authorize(creds)

SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1-mI71sC7TE-f8Gb9YPddhVGJrozKxLIdJlSBf2khJsA/edit"
SHEET_NAME = "院務會議請假紀錄"

# 群組推播
GROUP_IDS = [os.getenv("internal_medicine_group_id"), os.getenv("surgery_group_id")]

def open_meeting_leave_application(line_bot_api, meeting_name: str):
    flex_message = FlexSendMessage(
        alt_text=f"{meeting_name}請假申請開啟",
        contents={
            "type": "bubble",
            "size": "mega",
            "body": {
                "type": "box",
                "layout": "vertical",
                "spacing": "md",
                "contents": [
                    {"type": "text", "text": f"{meeting_name}請假申請", "weight": "bold", "size": "xl", "align": "center"},
                    {"type": "text", "text": f"請問您是否出席「{meeting_name}」？", "size": "md", "align": "center", "wrap": True},
                    {
                        "type": "button",
                        "style": "primary",
                        "color": "#00C851",
                        "action": {"type": "message", "label": "✅ 出席", "text": f"出席 {meeting_name}"}
                    },
                    {
                        "type": "button",
                        "style": "primary",
                        "color": "#ff4444",
                        "action": {"type": "message", "label": "❌ 請假", "text": f"請假 {meeting_name}"}
                    }
                ]
            }
        }
    )
    for group_id in GROUP_IDS:
        if group_id:
            try:
                line_bot_api.push_message(group_id, flex_message)
            except Exception as e:
                print(f"❌ 推播至群組失敗: {e}")

def handle_meeting_leave_response(event, line_bot_api, user_msg, user_id):
    try:
        if user_msg.startswith("出席 "):
            meeting_name = user_msg.replace("出席 ", "").strip()
            doctor_name = get_doctor_name(user_id)
            record_meeting_reply(user_id, doctor_name, meeting_name, "出席")
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"✅ 已紀錄您將出席【{meeting_name}】！謝謝。"))
            return True

        if user_msg.startswith("請假 "):
            meeting_name = user_msg.replace("請假 ", "").strip()
            set_state(user_id, f"ASK_REASON_{meeting_name}")
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"❓ 請問您無法出席【{meeting_name}】的原因？"))
            return True

        current_state = get_state(user_id)
        if current_state and current_state.startswith("ASK_REASON_"):
            meeting_name = current_state.replace("ASK_REASON_", "")
            doctor_name = get_doctor_name(user_id)
            reason = user_msg.strip() if user_msg.strip() else "未提供原因"
            record_meeting_reply(user_id, doctor_name, meeting_name, "請假", reason)
            clear_state(user_id)
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"✅ 已收到您的請假原因：【{reason}】"))

            push_leave_notification(doctor_name, meeting_name, reason)
            return True

    except Exception as e:
        print(f"❌ handle_meeting_leave_response 錯誤：{e}")
    return False

def record_meeting_reply(user_id, doctor_name, meeting_name, reply_type, reason=None):
    try:
        sheet = gc.open_by_url(SPREADSHEET_URL).worksheet(SHEET_NAME)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sheet.append_row([timestamp, user_id, doctor_name, meeting_name, reply_type, reason or ""])
    except Exception as e:
        print(f"❌ 寫入Google Sheets錯誤：{e}")

def push_leave_notification(doctor_name, meeting_name, reason):
    message = f"⚠️【{meeting_name}請假通知】\n{doctor_name} 醫師請假。\n原因：{reason}"
    for group_id in GROUP_IDS:
        if group_id:
            try:
                push_text_to_user(group_id, message)
            except Exception as e:
                print(f"❌ 請假推播錯誤: {e}")

def get_doctor_name(user_id):
    try:
        spreadsheet = gc.open_by_key("1fHf5XlbvLMd6ytAh_t8Bsi5ghToiQHZy1NlVfEG7VIo")
        sheet = spreadsheet.worksheet("UserMapping")
        records = sheet.get_all_records()
        for record in records:
            if record.get("user_id") == user_id:
                return record.get("name", "未知醫師")
    except Exception as e:
        print(f"❌ get_doctor_name 錯誤：{e}")
    return "未知醫師"
