# night_shift_fee_generator.py
# 每月自動產出 Word 夜點費申請表，依科別分檔並備份至 Google Drive

import os, json, gspread
from datetime import datetime
from collections import defaultdict
from io import BytesIO
from docx import Document
from oauth2client.service_account import ServiceAccountCredentials
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# ✅ 認證與服務初始化
SCOPE = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]
creds_dict = json.loads(os.environ.get("GOOGLE_CREDENTIALS"))

creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
gc = gspread.authorize(creds)

creds2 = Credentials.from_service_account_info(creds_dict, scopes=SCOPE)
drive_service = build('drive', 'v3', credentials=creds2)

# ✅ 基本設定
SHEET_ID = "1rtoP3e7D4FPzXDqv0yIOqYE9gwsdmFQSccODkbTZVDs"
WORKSHEET_NAME = "夜點費申請"
DRIVE_FOLDER_ID = "1s-joUzZQBHyCKmWZRD4F78qjvvEZ15Dq"

TEMPLATE_MAP = {
    "醫療部": "templates/醫療部_樣板.docx",
    "外科": "templates/外科_樣板.docx",
    "內科": "templates/內科_樣板.docx"
}

# ✅ 取得本月與民國年
this_month = datetime.now().strftime("%m").lstrip("0")
this_year = datetime.now().year - 1911

# ✅ 載入表單資料
try:
    sheet = gc.open_by_key(SHEET_ID).worksheet(WORKSHEET_NAME)
    data = sheet.get_all_records()
except Exception as e:
    print(f"❌ Google Sheets 載入失敗：{e}")
    exit()

# ✅ 整理成 {科別: [{姓名, 日期, 總班數}]}
output = defaultdict(list)
for row in data:
    try:
        name = row.get("醫師姓名", "").strip()
        dept = row.get("醫師科別", "").strip()
        date_str = str(row.get("日期", "")).strip()
        count = int(row.get("總班數", 1))

        if name and dept:
            output[dept].append({
                "name": name,
                "date": date_str,
                "count": count
            })
    except Exception as e:
        print(f"⚠️ 資料轉換錯誤：{row} → {e}")
        continue

# ✅ 逐科產出 Word 並上傳
for dept, records in output.items():
    template_path = TEMPLATE_MAP.get(dept)
    if not template_path or not os.path.exists(template_path):
        print(f"❌ 找不到科別「{dept}」的樣板：{template_path}")
        continue

    try:
        doc = Document(template_path)
        table = doc.tables[0]

        for rec in records:
            row = table.add_row().cells
            row[0].text = rec["name"]
            row[1].text = rec["date"]
            row[2].text = str(rec["count"])

        # 儲存到記憶體
        doc_io = BytesIO()
        doc.save(doc_io)
        doc_io.seek(0)

        filename = f"{this_year}年{this_month}月_{dept}_夜點費申請表.docx"
        file_metadata = {
            'name': filename,
            'parents': [DRIVE_FOLDER_ID]
        }
        media = MediaIoBaseUpload(doc_io, mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        file = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()

        print(f"✅ 已產出並上傳：{filename}（檔案ID：{file.get('id')}）")

    except Exception as e:
        print(f"❌ 產出或上傳失敗（科別：{dept}）：{e}")

print("🎉 所有科別夜點費申請表已完成產出並備份。")
