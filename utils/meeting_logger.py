# utils/meeting_logger.py

import gspread
import json
import os
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from gspread.exceptions import WorksheetNotFound

# ✅ 建立認證（用環境變數）
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
google_creds = json.loads(os.environ['GOOGLE_CREDENTIALS'])
creds = ServiceAccountCredentials.from_json_keyfile_dict(google_creds, scope)
gc = gspread.authorize(creds)

def log_meeting_reply(sheet_url, user_id, name, dept, reply, reason):
    try:
        sheet = gc.open_by_url(sheet_url).sheet1  # ✅ 預設為第一個分頁
        now = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
        sheet.append_row([now, user_id, name, dept, reply, reason])
        print(f"[LOG] ✅ 已寫入會議回覆：{name}, {reply}")
    except WorksheetNotFound:
        print("❌ 找不到工作表")
        raise
    except Exception as e:
        print(f"❌ log_meeting_reply 寫入失敗：{e}")
        raise
