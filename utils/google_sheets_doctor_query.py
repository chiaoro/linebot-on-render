# utils/google_sheets_doctor_query.py
import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ✅ Google Sheets 認證
def get_gspread_client():
    creds_dict = json.loads(os.getenv("GOOGLE_CREDENTIALS"))
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    return gspread.authorize(creds)

# ✅ 查詢醫師資料
def get_doctor_info(name):
    SHEET_URL = os.getenv("DOCTOR_SHEET_URL")
    gc = get_gspread_client()
    sheet = gc.open_by_url(SHEET_URL).sheet1
    data = sheet.get_all_records()

    for row in data:
        if row["姓名"] == name:
            return {
                "姓名": row["姓名"],
                "科別": row.get("科別", "無"),
                "職稱": row.get("職稱", "無"),
                "手機": row.get("手機", "無"),
                "地址": row.get("地址", "無"),
                "在澎地址": row.get("在澎地址", "無"),
                "Email": row.get("Email", "無")
            }
    return None
