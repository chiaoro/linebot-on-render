# utils/night_shift_fee_generator.py

import os
import json
from datetime import datetime, timedelta
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from docx import Document
from google.oauth2 import service_account
from googleapiclient.discovery import build
import io
from googleapiclient.http import MediaIoBaseUpload

# ✅ Google Sheets 認證
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = json.loads(os.getenv("GOOGLE_CREDENTIALS", "{}"))
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
gc = gspread.authorize(creds)

# ✅ Google Drive 認證（for 上傳 Word）
SERVICE_ACCOUNT_INFO = json.loads(os.getenv("GOOGLE_CREDENTIALS", "{}"))
credentials = service_account.Credentials.from_service_account_info(
    SERVICE_ACCOUNT_INFO,
    scopes=['https://www.googleapis.com/auth/drive']
)
drive_service = build('drive', 'v3', credentials=credentials)

# ✅ 固定變數
NIGHT_FEE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1rtoP3e7D4FPzXDqv0yIOqYE9gwsdmFQSccODkbTZVDs/edit"
USER_MAPPING_URL = "https://docs.google.com/spreadsheets/d/1fHf5XlbvLMd6ytAh_t8Bsi5ghToiQHZy1NlVfEG7VIo/edit"
UPLOAD_FOLDER_ID = os.getenv("NIGHT_FEE_FOLDER_ID")

# ✅ Word 樣板對照表
TEMPLATE_MAP = {
    "醫療部": "1lCMQxsNh7bWeWKDPYi9k9r3GWnG1RhpV1P487vNBrww",
    "內科":   "179bI7Fx9kSm7vz19wsTv51-ULAnH9llC8Yc_3wLhviM",
    "外科":   "1KG1eRI7ySvoczAGpCQKIQM0AIw3LkOZiTfKaCWrQigE"
}

def run_generate_night_fee_word():
    today = datetime.today()
    last_month = today.month - 1 if today.month > 1 else 12
    year = today.year if today.month > 1 else today.year - 1

    # 開啟試算表
    sheet = gc.open_by_url(NIGHT_FEE_SHEET_URL).worksheet("夜點費申請")
    mapping = gc.open_by_url(USER_MAPPING_URL).worksheet("UserMapping")

    records = sheet.get_all_records()
    mappings = mapping.get_all_records()

    # 建立姓名 -> 科別對照表
    doctor_to_dept = {m["姓名"]: m.get("科別", "醫療部") for m in mappings}

    # 群組資料（並記下 row index）
    grouped = {}
    all_rows = sheet.get_all_values()

    for idx, row in enumerate(all_rows[1:], start=2):  # skip header
        name = row[0]
        date = row[2] if len(row) > 2 else ""
        status = row[4] if len(row) > 4 else ""
        if name and not status:
            if name not in grouped:
                grouped[name] = {"dates": [], "count": 0, "rows": []}
            grouped[name]["dates"].append(date)
            grouped[name]["count"] += 1
            grouped[name]["rows"].append(idx)

    for doctor, info in grouped.items():
        dept = doctor_to_dept.get(doctor, "醫療部")
        template_id = TEMPLATE_MAP.get(dept, TEMPLATE_MAP["醫療部"])

        # 下載 Word 樣板
        template_file = drive_service.files().get_media(fileId=template_id).execute()
        document = Document(io.BytesIO(template_file))

        # 替換變數
        for p in document.paragraphs:
            if "{{醫師姓名}}" in p.text:
                p.text = p.text.replace("{{醫師姓名}}", doctor)
            if "{{年月}}" in p.text:
                p.text = p.text.replace("{{年月}}", f"{year}/{last_month:02d}")
            if "{{日期}}" in p.text:
                p.text = p.text.replace("{{日期}}", ", ".join(info["dates"]))
            if "{{班數}}" in p.text:
                p.text = p.text.replace("{{班數}}", str(info["count"]))

        # 儲存
        output_stream = io.BytesIO()
        document.save(output_stream)
        output_stream.seek(0)

        # 上傳
        file_metadata = {
            "name": f"{doctor}_{year}_{last_month:02d}_夜點費申請.docx",
            "parents": [UPLOAD_FOLDER_ID]
        }
        media = MediaIoBaseUpload(output_stream, mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()

        # ✅ 標記試算表已產出
        for r in info["rows"]:
            sheet.update_cell(r, 5, "已產出")  # 第 5 欄為狀態
