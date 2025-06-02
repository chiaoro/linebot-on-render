import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from gspread.exceptions import WorksheetNotFound

# ✅ 使用 Render 的 GOOGLE_CREDENTIALS 環境變數初始化授權
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
google_creds = json.loads(os.environ["GOOGLE_CREDENTIALS"])
creds = ServiceAccountCredentials.from_json_keyfile_dict(google_creds, scope)
gc = gspread.authorize(creds)

def get_doctor_info(sheet_url, user_id):
    try:
        sheet = gc.open_by_url(sheet_url).worksheet("UserMapping")  # ✅ 改成正確分頁名稱
    except WorksheetNotFound:
        print("❌ 找不到工作表：UserMapping")
        return None, None
    except Exception as e:
        print(f"❌ Google Sheet 連線失敗：{e}")
        return None, None

    try:
        data = sheet.get_all_values()
        for i in range(1, len(data)):  # 從第 2 列開始（跳過標題）
            row = data[i]
            line_id = row[0].strip()
            name = row[1].strip() if len(row) > 1 else "未知"
            dept = row[2].strip() if len(row) > 2 else "未知"

            if line_id == user_id:
                print(f"[DEBUG] ✅ 找到醫師資訊：{name}（{dept}）")
                return name, dept

    except Exception as e:
        print(f"❌ 讀取資料失敗：{e}")

    print(f"⚠️ 查無 user_id={user_id} 的醫師資訊")
    return None, None
