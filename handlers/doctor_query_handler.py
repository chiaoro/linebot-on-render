from linebot.models import TextSendMessage
from utils.session_manager import user_sessions
import gspread
import json
import os

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

# ✅ 主流程
def handle_doctor_query(event, line_bot_api, user_id, text, sheet_url, allowed_ids):
    # ✅ 進入查詢模式
    if text == "查詢醫師資料（限制使用）":
        if user_id not in allowed_ids:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="⚠️ 你沒有使用此功能的權限"))
            return True
        start_doctor_query(user_id)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請輸入欲查詢的醫師姓名"))
        return True

    # ✅ 第二階段：使用者輸入姓名
    if is_in_doctor_query_session(user_id):
        doctor_name = text.strip()
        info = get_doctor_info_from_sheet(sheet_url, doctor_name)

        if info:
            reply_text = format_doctor_info(info)
        else:
            reply_text = f"❌ 找不到「{doctor_name}」的資料，請確認姓名是否正確。"

        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))
        clear_doctor_query(user_id)
        return True

    return False

# ✅ 從 Google Sheet 讀取醫師資料
def get_doctor_info_from_sheet(sheet_url, name):
    gc = gspread.service_account_from_dict(get_google_credentials())
    sh = gc.open_by_url(sheet_url)
    ws = sh.sheet1
    data = ws.get_all_records()

    for row in data:
        if row.get("姓名") == name:  # 完全比對
            return row
    return None

# ✅ 讀取 Google API 憑證
def get_google_credentials():
    return json.loads(os.getenv("GOOGLE_CREDENTIALS"))

# ✅ 格式化輸出
def format_doctor_info(info):
    return (
        f"✅ 醫師資訊：\n"
        f"姓名：{info.get('姓名','')}\n"
        f"出生年月：{info.get('出生年月','')}\n"
        f"Line ID：{info.get('Lind ID','')}\n"
        f"性別：{info.get('性別','')}\n"
        f"年齡：{info.get('年齡','')}\n"
        f"公務機：{info.get('公務機','')}\n"
        f"私人手機：{info.get('私人手機','')}\n"
        f"地址：{info.get('地址','')}\n"
        f"在澎地址：{info.get('在澎地址','')}\n"
        f"Email：{info.get('email','')}\n"
        f"緊急聯絡人姓名：{info.get('緊急聯絡人姓名','')}\n"
        f"緊急聯絡人關係：{info.get('緊急聯絡人關係','')}\n"
        f"緊急聯絡人電話：{info.get('緊急聯絡人電話','')}"
    )
