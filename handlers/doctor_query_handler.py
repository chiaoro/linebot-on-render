from linebot.models import FlexSendMessage, TextSendMessage
from utils.session_manager import user_sessions
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import json

# ✅ Google Sheets 設定
SHEET_URL = "https://docs.google.com/spreadsheets/d/14mU_Hqu0M971HAMTZtSFGvvPLu9oPbtx7-9BvqRX9Iw/edit?usp=sharing"
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# ✅ 使用 Render 環境變數 GOOGLE_CREDENTIALS
google_credentials = os.getenv("GOOGLE_CREDENTIALS")
if not google_credentials:
    raise ValueError("❌ GOOGLE_CREDENTIALS 環境變數未設定")

service_account_info = json.loads(google_credentials)
creds = ServiceAccountCredentials.from_json_keyfile_dict(service_account_info, SCOPE)
client = gspread.authorize(creds)
sheet = client.open_by_url(SHEET_URL).sheet1  # 預設第一個工作表

# ✅ 啟動醫師查詢模式
def start_doctor_query(user_id):
    user_sessions[user_id] = {"mode": "doctor_query"}
    print(f"✅ {user_id} 啟動醫師查詢模式")

# ✅ 判斷是否在查詢流程中
def is_in_doctor_query_session(user_id):
    return user_id in user_sessions and user_sessions[user_id].get("mode") == "doctor_query"

# ✅ 清除查詢狀態
def clear_doctor_query(user_id):
    if user_id in user_sessions:
        del user_sessions[user_id]

# ✅ 取得醫師資料
def get_doctor_info_by_name(name):
    data = sheet.get_all_records()
    for row in data:
        if str(row.get("姓名", "")).strip() == name.strip():
            return row
    return None

# ✅ Flex Message 產生器
def generate_doctor_flex(info):
    return {
        "type": "bubble",
        "size": "giga",
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {"type": "text", "text": "✅ 醫師資訊", "weight": "bold", "size": "xl", "color": "#1DB446"},
                {"type": "separator", "margin": "md"},
                {"type": "box", "layout": "vertical", "margin": "lg", "spacing": "sm", "contents": [
                    {"type": "text", "text": f"姓名：{info.get('姓名', '')}", "wrap": True},
                    {"type": "text", "text": f"出生年月：{info.get('出生年月', '')}", "wrap": True},
                    {"type": "text", "text": f"Line ID：{info.get('Line ID', '')}", "wrap": True},
                    {"type": "text", "text": f"性別：{info.get('性別', '')}", "wrap": True},
                    {"type": "text", "text": f"年齡：{info.get('年齡', '')}", "wrap": True},
                    {"type": "text", "text": f"公務機：{info.get('公務機', '')}", "wrap": True},
                    {"type": "text", "text": f"私人手機：{info.get('私人手機', '')}", "wrap": True},
                    {"type": "text", "text": f"地址：{info.get('地址', '')}", "wrap": True},
                    {"type": "text", "text": f"在澎地址：{info.get('在澎地址', '')}", "wrap": True},
                    {"type": "text", "text": f"Email：{info.get('email', '')}", "wrap": True},
                    {"type": "text", "text": f"緊急聯絡人姓名：{info.get('緊急連絡人姓名', '')}", "wrap": True},
                    {"type": "text", "text": f"緊急聯絡人關係：{info.get('緊急連絡人關係', '')}", "wrap": True},
                    {"type": "text", "text": f"緊急聯絡人電話：{info.get('緊急連絡人電話', '')}", "wrap": True}
                ]}
            ]
        }
    }

# ✅ 主流程
def handle_doctor_query(event, line_bot_api, user_id, text):
    from app import ALLOWED_USER_IDS
    # ✅ 白名單檢查
    if text == "查詢醫師資料（限制使用）":
        if user_id not in ALLOWED_USER_IDS:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="⚠️ 你沒有使用此功能的權限"))
            return
        start_doctor_query(user_id)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請輸入欲查詢的醫師姓名"))
        return

    # ✅ 是否在查詢模式
    if is_in_doctor_query_session(user_id):
        doctor_name = text.strip()
        info = get_doctor_info_by_name(doctor_name)

        if info:
            flex_message = FlexSendMessage(
                alt_text="醫師資訊",
                contents=generate_doctor_flex(info)
            )
            line_bot_api.reply_message(event.reply_token, flex_message)
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="⚠️ 查無此醫師資料，請確認姓名是否正確"))
        
        clear_doctor_query(user_id)
