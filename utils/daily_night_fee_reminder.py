import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv
from linebot import LineBotApi
from linebot.models import TextSendMessage

# 載入環境變數
load_dotenv()
line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))

# Google Sheets 認證
SCOPE = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds_dict = json.loads(os.getenv("GOOGLE_CREDENTIALS"))
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
gc = gspread.authorize(creds)

# 表單網址
REMINDER_SHEET_URL = "https://docs.google.com/spreadsheets/d/1rtoP3e7D4FPzXDqv0yIOqYE9gwsdmFQSccODkbTZVDs/edit"
USER_SHEET_URL = "https://docs.google.com/spreadsheets/d/1fHf5XlbvLMd6ytAh_t8Bsi5ghToiQHZy1NlVfEG7VIo/edit"

def send_night_fee_reminders():
    reminder_ws = gc.open_by_url(REMINDER_SHEET_URL).worksheet("夜點費提醒名單")
    user_ws = gc.open_by_url(USER_SHEET_URL).worksheet("UserMapping")

    reminder_data = reminder_ws.get_all_records()
    user_data = user_ws.get_all_records()

    # 建立醫師姓名 ➜ userId 對照
    name_to_id = {row["name"]: row["userId"] for row in user_data if row.get("name") and row.get("userId")}

    for row in reminder_data:
        name = row.get("醫師姓名", "").strip()
        status = row.get("狀態", "").strip()
        if name and not status:
            user_id = name_to_id.get(name)
            if user_id:
                try:
                    line_bot_api.push_message(user_id, TextSendMessage(
                        text=f"📌 親愛的{name}醫師，提醒您記得填寫本月夜點費申請表單唷～"
                    ))
                except Exception as e:
                    print(f"❌ 推播給 {name} 失敗：{e}")

