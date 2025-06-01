import json
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from gspread.exceptions import WorksheetNotFound
from utils.google_sheets import get_doctor_info

# ✅ 使用環境變數初始化（Render 或部署用）
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
google_creds = json.loads(os.environ['GOOGLE_CREDENTIALS'])
creds = ServiceAccountCredentials.from_json_keyfile_dict(google_creds, scope)
gc = gspread.authorize(creds)

def get_doctor_info(sheet_url, user_id):
    try:
        sheet = gc.open_by_url(sheet_url).worksheet("UserMapping")
    except WorksheetNotFound:
        print("❌ 找不到工作表：UserMapping")
        return None, None
    except Exception as e:
        print(f"❌ Google Sheet 連線失敗：{e}")
        return None, None

    try:
        rows = sheet.get_all_records()
        for row in rows:
            if row.get("user_id") == user_id:
                return row.get("name"), row.get("dept")
    except Exception as e:
        print(f"❌ 讀取資料失敗：{e}")

    return None, None



def get_doctor_name(sheet_url, user_id):
    doctor_info = get_doctor_info(sheet_url)
    return doctor_info.get(user_id, "未知醫師")
