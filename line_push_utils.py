#✅推播模組

import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv
from linebot import LineBotApi
from linebot.models import TextSendMessage

load_dotenv()

# ✅ Google Sheets 認證
SCOPE = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds_dict = json.loads(os.environ.get("GOOGLE_CREDENTIALS"))
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
gc = gspread.authorize(creds)

# ✅ LINE Bot 初始化
line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))

# ✅ 開啟使用者對照表
user_sheet = gc.open_by_url("https://docs.google.com/spreadsheets/d/1fHf5XlbvLMd6ytAh_t8Bsi5ghToiQHZy1NlVfEG7VIo/edit").sheet1
user_data = user_sheet.get_all_records()

# ✅ 根據醫師姓名推播訊息
def push_to_doctor(name, message):
    for row in user_data:
        if row["醫師姓名"] == name:
            user_id = row["LINE 使用者 ID"]
            try:
                line_bot_api.push_message(user_id, TextSendMessage(text=message))
                print(f"✅ 已推播給 {name}")
            except Exception as e:
                print(f"❌ 推播失敗給 {name}：{e}")
            return
    print(f"❌ 找不到醫師：{name}")
