# meeting_leave_scheduler.py
# ✅ 每天自動從試算表掃描即將到來的會議，提早推播 Flex 請假申請
# by 小秘 GPT

import os
import json
import gspread
from datetime import datetime, timedelta
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv
from meeting_leave import open_meeting_leave_application

load_dotenv()

# ✅ Google Sheets 認證
SCOPE = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds_dict = json.loads(os.environ.get("GOOGLE_CREDENTIALS"))
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
gc = gspread.authorize(creds)

# ✅ 會議排程表設定
SCHEDULE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1XpX1l7Uf93XWNEYdZsHx-3IXpPf4Sb9Zl0ARGa4Iy5c/edit"
SHEET_NAME = "會議排程"  # 你可以改成你自己設定的分頁名稱

# ✅ 幾天前推播申請
DAYS_BEFORE = 7

def run_meeting_leave_scheduler(line_bot_api):
    try:
        sheet = gc.open_by_url(SCHEDULE_SHEET_URL).worksheet(SHEET_NAME)
        records = sheet.get_all_records()

        today = datetime.now().date()
        target_date = today + timedelta(days=DAYS_BEFORE)

        for record in records:
            meeting_date_str = record.get("日期", "").strip()
            meeting_name = record.get("會議名稱", "").strip()

            if not meeting_date_str:
                continue  # 沒填日期，跳過

            try:
                meeting_date = datetime.strptime(meeting_date_str, "%Y/%m/%d").date()
            except Exception as e:
                print(f"❌ 日期格式錯誤：{meeting_date_str}，錯誤訊息：{e}")
                continue  # 格式錯誤跳過

            if meeting_date == target_date:
                meeting_name = meeting_name if meeting_name else f"{meeting_date.strftime('%m/%d')} 院務會議"
                print(f"✅ 發現符合條件的會議：{meeting_name}")
                open_meeting_leave_application(line_bot_api, meeting_name)

    except Exception as e:
        print(f"❌ 執行會議排程檢查時錯誤：{e}")
