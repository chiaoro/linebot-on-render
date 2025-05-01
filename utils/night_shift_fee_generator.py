# ✅ night_shift_fee_generator.py
# 每月產出夜點費申請表：每科別一張 Word 總表

import os
import json
import gspread
from docx import Document
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials

# ✅ Google Sheets 認證
SCOPE = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds_dict = json.loads(os.environ.get("GOOGLE_CREDENTIALS"))
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
gc = gspread.authorize(creds)

# ✅ 試算表與模板資料夾設定
SHEET_ID = "1rtoP3e7D4FPzXDqv0yIOqYE9gwsdmFQSccODkbTZVDs"
TEMPLATE_MAP = {
    "醫療部": "templates/醫療部_夜點費申請表.docx",
    "外科": "templates/外科_夜點費申請表.docx"
}
SAVE_DIR = "/mnt/data/generated_words"

# ✅ 載入資料
sheet = gc.open_by_key(SHEET_ID).worksheet("夜點費申請")
data = sheet.get_all_records()

# ✅ 整理成：{科別: [{姓名, 日期清單, 總班數}]}
from collections import defaultdict
from pathlib import Path

output = defaultdict(list)

for row in data:
    name = row.get("醫師姓名", "")
    dept = row.get("醫師科別", "")
    date = row.get("日期", "")
    count = row.get("總班數", 1)
    if not name or not dept:
        continue
    output[dept].append({"name": name, "date": date, "count": count})

# ✅ 按科別產出 Word
Path(SAVE_DIR).mkdir(parents=True, exist_ok=True)
this_month = datetime.now().strftime("%m").lstrip("0")
this_year = datetime.now().year - 1911

for dept, records in output.items():
    template_path = TEMPLATE_MAP.get(dept)
    if not template_path or not os.path.exists(template_path):
        continue

    doc = Document(template_path)
    table = doc.tables[0]  # 假設表格在第一個表格

    for rec in records:
        row = table.add_row().cells
        row[0].text = rec["name"]
        row[1].text = rec["date"]
        row[2].text = str(rec["count"])

    filename = f"{this_year}年{this_month}月_{dept}_夜點費申請表.docx"
    filepath = os.path.join(SAVE_DIR, filename)
    doc.save(filepath)

print(f"✅ 全部申請表已產出至 {SAVE_DIR}")
