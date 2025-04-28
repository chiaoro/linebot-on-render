# utils/night_shift_fee_generator.py

import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from docx import Document
from dotenv import load_dotenv

load_dotenv()

# ✅ Google Sheets 認證
SCOPE = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(os.getenv("GOOGLE_CREDENTIALS")), SCOPE)
gc = gspread.authorize(creds)

# ✅ 連結夜點費紀錄表
night_fee_sheet = gc.open_by_url("https://docs.google.com/spreadsheets/d/1rtoP3e7D4FPzXDqv0yIOqYE9gwsdmFQSccODkbTZVDs/edit")

# ✅ Word 樣板連結
template_map = {
    "醫療部": "https://docs.google.com/document/d/1lCMQxsNh7bWeWKDPYi9k9r3GWnG1RhpV1P487vNBrww/export?format=docx",
    "內科": "https://docs.google.com/document/d/179bI7Fx9kSm7vz19wsTv51-ULAnH9llC8Yc_3bLhviM/export?format=docx",
    "外科": "https://docs.google.com/document/d/1KG1eRI7ySvoczAGpCQKIQM0AIw3LkOZiTfKaCWrQigE/export?format=docx"
}

# ✅ 存檔資料夾
SAVE_FOLDER = "/mnt/data/night_fee_docs"

os.makedirs(SAVE_FOLDER, exist_ok=True)

# ✅ 產生夜點費申請 Word 檔
def run_generate_night_fee_word():
    today = datetime.now()
    last_month = today.month - 1 or 12
    last_year = today.year if today.month != 1 else today.year - 1
    month_str = f"{last_year}-{str(last_month).zfill(2)}"

    for dept in ["醫療部", "內科", "外科"]:
        try:
            worksheet = night_fee_sheet.worksheet(dept)
        except gspread.WorksheetNotFound:
            print(f"❌ 找不到科別：{dept}")
            continue

        data = worksheet.get_all_records()

        doctors_data = {}
        for row in data:
            if row.get("月份") == month_str and row.get("狀態") == "申請":
                name = row.get("醫師姓名")
                shift_date = row.get("值班日期")
                if not name or not shift_date:
                    continue
                if name not in doctors_data:
                    doctors_data[name] = []
                doctors_data[name].append(shift_date)

        if not doctors_data:
            print(f"⚠️ {dept} 沒有資料可以產生")
            continue

        # 下載樣板
        import requests
        template_url = template_map.get(dept)
        if not template_url:
            print(f"❌ {dept} 找不到樣板")
            continue

        resp = requests.get(template_url)
        template_path = os.path.join(SAVE_FOLDER, f"{dept}_template.docx")
        with open(template_path, "wb") as f:
            f.write(resp.content)

        # 產生每個醫師的 Word
        for doctor_name, dates in doctors_data.items():
            doc = Document(template_path)
            for p in doc.paragraphs:
                if "{{醫師姓名}}" in p.text:
                    p.text = p.text.replace("{{醫師姓名}}", doctor_name)
                if "{{月份}}" in p.text:
                    p.text = p.text.replace("{{月份}}", f"{last_year}年{str(last_month).zfill(2)}月")
                if "{{值班日期}}" in p.text:
                    p.text = p.text.replace("{{值班日期}}", "、".join(dates))
                if "{{班數}}" in p.text:
                    p.text = p.text.replace("{{班數}}", str(len(dates)))

            save_path = os.path.join(SAVE_FOLDER, f"{dept}_{doctor_name}_夜點費申請.docx")
            doc.save(save_path)
            print(f"✅ 已產生：{save_path}")
