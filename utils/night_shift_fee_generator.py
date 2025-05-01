# ✅ night_shift_fee_generator.py
# 每月產出夜點費申請表：每科別一張 Word 總表，並自動備份到 Google Drive（不寫入本地）

import os
import json
import gspread
from docx import Document
from datetime import datetime
from io import BytesIO
from oauth2client.service_account import ServiceAccountCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2.service_account import Credentials
from collections import defaultdict

# ✅ Google Sheets + Drive 認證
SCOPE = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
creds_dict = json.loads(os.environ.get("GOOGLE_CREDENTIALS"))
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
gc = gspread.authorize(creds)

creds2 = Credentials.from_service_account_info(creds_dict, scopes=SCOPE)
drive_service = build('drive', 'v3', credentials=creds2)

# ✅ 設定
SHEET_ID = "1rtoP3e7D4FPzXDqv0yIOqYE9gwsdmFQSccODkbTZVDs"
TEMPLATE_MAP = {
    "醫療部": "templates/醫療部_夜點費申請表.docx",
    "外科": "templates/外科_夜點費申請表.docx",
    "內科": "templates/內科_夜點費申請表.docx"
}
DRIVE_FOLDER_ID = "1s-joUzZQBHyCKmWZRD4F78qjvvEZ15Dq"

# ✅ 載入試算表資料
sheet = gc.open_by_key(SHEET_ID).worksheet("夜點費申請")
data = sheet.get_all_records()

# ✅ 整理成：{科別: [{姓名, 日期清單, 總班數}]}
output = defaultdict(list)
for row in data:
    name = row.get("醫師姓名", "")
    dept = row.get("醫師科別", "")
    date = row.get("日期", "")
    count = row.get("總班數", 1)
    if not name or not dept:
        continue
    output[dept].append({"name": name, "date": date, "count": count})

# ✅ 產出每科別 Word 並上傳
this_month = datetime.now().strftime("%m").lstrip("0")
this_year = datetime.now().year - 1911

for dept, records in output.items():
    template_path = TEMPLATE_MAP.get(dept)
    if not template_path or not os.path.exists(template_path):
        print(f"❌ 找不到科別「{dept}」的樣板：{template_path}")
        continue

    doc = Document(template_path)
    table = doc.tables[0]

    for rec in records:
        row = table.add_row().cells
        row[0].text = rec["name"]
        row[1].text = rec["date"]
        row[2].text = str(rec["count"])

    # 存到記憶體
    doc_io = BytesIO()
    doc.save(doc_io)
    doc_io.seek(0)

    filename = f"{this_year}年{this_month}月_{dept}_夜點費申請表.docx"
    file_metadata = {
        'name': filename,
        'parents': [DRIVE_FOLDER_ID]
    }
    media = MediaIoBaseUpload(doc_io, mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
    drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()

print("✅ 全部夜點費申請表已產出並成功上傳至 Google Drive。")
