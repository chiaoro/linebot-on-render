# utils/daily_notifier.py

import os
import json
import gspread
from dotenv import load_dotenv
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials
from utils.line_push_utils import push_to_doctor

load_dotenv()

# Google Sheets 認證
SCOPE = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds_dict = json.loads(os.getenv("GOOGLE_CREDENTIALS", "{}"))
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
gc = gspread.authorize(creds)

def run_daily_push():
    """每日推播個人提醒（讀取每日推播表單）"""

    # 打開每日推播的 Google Sheets
    sheet_url = os.getenv("DAILY_PUSH_SHEET_URL")  # 環境變數：每日推播表單網址
    if not sheet_url:
        print("❌ 環境變數 DAILY_PUSH_SHEET_URL 未設定")
        return

    sheet = gc.open_by_url(sheet_url).worksheet("每日推播")
    data = sheet.get_all_records()

    today = datetime.now().strftime("%Y-%m-%d")

    for row in data:
        push_date = row.get("推播日期")
        user_id = row.get("LINE_ID")
        message = row.get("推播內容")

        if not push_date or not user_id or not message:
            continue  # 資料不完整就跳過

        if push_date == today:
            try:
                push_to_doctor(user_id, message)
                print(f"✅ 已推播：{user_id} - {message}")
            except Exception as e:
                print(f"❌ 推播錯誤：{user_id} - {e}")
