# handlers/doctor_query_handler.py
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from linebot.models import TextSendMessage
import os
import json

# ✅ 使用者狀態暫存（記錄哪些人正在進行查詢流程）
user_query_state = {}

# ✅ 取得 Google Sheets 資料
def fetch_doctor_data(sheet_url, doctor_name):
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = json.loads(os.getenv("GOOGLE_CREDENTIALS"))
        client = gspread.service_account_from_dict(creds)
        sheet = client.open_by_url(sheet_url).sheet1
        data = sheet.get_all_records()
        for row in data:
            if row.get("姓名") == doctor_name.strip():
                return row
        return None
    except Exception as e:
        print(f"❌ Google Sheets 錯誤: {e}")
        return None

# ✅ 檢查是否觸發查詢流程
def is_doctor_query_trigger(user_id, text, allowed_ids):
    return text == "醫師資訊查詢（限制使用）" and user_id in allowed_ids

# ✅ 主流程
def handle_doctor_query(event, line_bot_api, user_id, text, sheet_url):
    # ✅ 白名單檢查
    allowed_ids = os.getenv("ALLOWED_USER_IDS", "").split(",")
    if user_id not in allowed_ids:
        return False  # 不處理

    # ✅ 如果觸發關鍵字，設定狀態
    if text == "醫師資訊查詢（限制使用）":
        user_query_state[user_id] = True
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請輸入欲查詢的醫師姓名"))
        return True

    # ✅ 如果使用者正在查詢狀態
    if user_query_state.get(user_id):
        doctor_name = text.strip()
        doctor_data = fetch_doctor_data(sheet_url, doctor_name)

        if doctor_data:
            message = (
                f"姓名：{doctor_data.get('姓名')}\n"
                f"出生年月：{doctor_data.get('出生年月')}\n"
                f"Lind ID：{doctor_data.get('Lind ID')}\n"
                f"性別：{doctor_data.get('性別')}\n"
                f"年齡：{doctor_data.get('年齡')}\n"
                f"公務機：{doctor_data.get('公務機')}\n"
                f"私人手機：{doctor_data.get('私人手機')}\n"
                f"地址：{doctor_data.get('地址')}\n"
                f"在澎地址：{doctor_data.get('在澎地址')}\n"
                f"email：{doctor_data.get('email')}\n"
                f"緊急聯絡人姓名：{doctor_data.get('緊急聯絡人姓名')}\n"
                f"緊急聯絡人關係：{doctor_data.get('緊急聯絡人關係')}\n"
                f"緊急聯絡人電話：{doctor_data.get('緊急聯絡人電話')}\n"
            )
        else:
            message = "❌ 查無此醫師資料，請確認姓名是否正確"

        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=message))
        user_query_state.pop(user_id, None)  # ✅ 清除狀態
        return True

    return False
