# utils/night_shift_fee_generator.py

import os, json
from datetime import datetime, timedelta
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from docx import Document
from google.oauth2 import service_account
from googleapiclient.discovery import build
import io
from googleapiclient.http import MediaIoBaseUpload

# ✅ Google Sheets認證
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


# ✅ 環境變數
SHEET_URL = os.getenv("SHEET_URL")  # ← 正確
USER_MAPPING_URL = os.getenv("DOCTOR_SHEET_URL")
UPLOAD_FOLDER_ID = os.getenv("NIGHT_FEE_FOLDER_ID")

# ✅ Word樣板設定
TEMPLATE_MAP = {
    "醫療部": "1lCMQxsNh7bWeWKDPYi9k9r3GWnG1RhpV1P487vNBrww",  # 醫療部樣板ID
    "內科": "179bI7Fx9kSm7vz19wsTv51-ULAnH9llC8Yc_3wLhviM",    # 內科樣板ID
    "外科": "1KG1eRI7ySvoczAGpCQKIQM0AIw3LkOZiTfKaCWrQigE"     # 外科樣板ID
}

def run_generate_night_fee_word():
    today = datetime.today()
    last_month = today.month - 1 if today.month > 1 else 12
    year = today.year if today.month > 1 else today.year - 1

    # 讀取資料
    sheet = gc.open_by_url(SHEET_URL).worksheet("夜點費申請")
    rows = sheet.get_all_records()
    
    user_mapping_sheet = gc.open_by_url(USER_MAPPING_URL).worksheet("UserMapping")
    mappings = user_mapping_sheet.get_all_records()
    doctor_to_dept = {m["姓名"]: m.get("科別", "醫療部") for m in mappings}

    for row in rows:
        doctor = row.get("醫師姓名", "").strip()
        dept = row.get("醫師科別", "").strip()
        dates = row.get("日期", "").strip()
        total = row.get("總班數", "")

        if not doctor or not dates:
            continue

        template_id = TEMPLATE_MAP.get(dept, TEMPLATE_MAP["醫療部"])

        try:
            # 下載模板
            template_file = drive_service.files().get_media(fileId=template_id).execute()
            document = Document(io.BytesIO(template_file))

            # 替換欄位
            for p in document.paragraphs:
                p.text = p.text.replace("{{醫師姓名}}", doctor)
                p.text = p.text.replace("{{年月}}", f"{year}/{last_month:02d}")
                p.text = p.text.replace("{{值班日期}}", dates)
                p.text = p.text.replace("{{總班數}}", str(total))

            # 儲存
            output_stream = io.BytesIO()
            document.save(output_stream)
            output_stream.seek(0)

            # 上傳
            filename = f"{doctor}_{year}_{last_month:02d}_夜點費申請.docx"
            file_metadata = {"name": filename, "parents": [UPLOAD_FOLDER_ID]}
            media = MediaIoBaseUpload(output_stream, mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
            drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        except Exception as e:
            print(f"❌ {doctor} Word 產生失敗：{str(e)}")
