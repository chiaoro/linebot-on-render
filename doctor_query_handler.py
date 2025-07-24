import os
import json
import base64
from linebot.models import TextSendMessage, FlexSendMessage
from google.oauth2 import service_account
from googleapiclient.discovery import build
from utils.line_flex import build_doctor_flex

# ✅ 環境變數
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
GOOGLE_SERVICE_ACCOUNT_JSON = json.loads(base64.b64decode(os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")).decode())

# ✅ 白名單（允許查詢的 LINE User ID）
ALLOWED_USER_IDS = ["Uxxxxxx1", "Uxxxxxx2"]

# ✅ 使用者對話狀態
user_session = {}

def get_sheets_service():
    creds = service_account.Credentials.from_service_account_info(
        GOOGLE_SERVICE_ACCOUNT_JSON,
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
    )
    return build("sheets", "v4", credentials=creds)




def query_doctor(name):
    service = get_sheets_service()
    sheet = service.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID, range="醫師資料!A2:P"
    ).execute()
    rows = sheet.get("values", [])
    for row in rows:
        if len(row) > 4 and row[4] == name:
            return {
                "姓名": row[4],
                "出生年月": row[5],
                "性別": row[6],
                "年齡": row[7],
                "公務機": row[8],
                "私人手機": row[9],
                "地址": row[10],
                "在澎地址": row[11],
                "email": row[12],
                "緊急聯絡人": f"{row[13]} ({row[14]}) {row[15]}"
            }
    return None







def handle_doctor_query(event, line_bot_api):
    user_id = event.source.user_id
    text = event.message.text.strip()

    # ✅ 啟動功能
    if text == "查詢醫師資料(限制使用)":
        if user_id in ALLOWED_USER_IDS:
            user_session[user_id] = {"step": 1}
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請輸入欲查詢醫師姓名："))
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="❌ 您沒有權限使用此功能"))
        return

    # ✅ 第二步：輸入姓名
    if user_id in user_session and user_session[user_id].get("step") == 1:
        doctor_name = text
        data = query_doctor(doctor_name)
        if data:
            flex_message = build_doctor_flex(data)
            line_bot_api.reply_message(event.reply_token, FlexSendMessage(alt_text="醫師資料", contents=flex_message))
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="找不到該醫師資料"))
        user_session.pop(user_id, None)