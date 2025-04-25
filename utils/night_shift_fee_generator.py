import os, json
from datetime import datetime, timedelta
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from docx import Document
from docx.shared import Pt
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# ✅ Google Sheets 認證
SCOPE = [
    'https://spreadsheets.google.com/feeds',
    'https://www.googleapis.com/auth/drive'
]
creds_dict = json.loads(os.environ.get("GOOGLE_CREDENTIALS"))
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
gc = gspread.authorize(creds)

# ✅ Google Drive API for upload
DRIVE = build('drive', 'v3', credentials=creds)
FOLDER_ID = "1s-joUzZQBHyCKmWZRD4F78qjvvEZ15Dq"  # 你的雲端資料夾 ID

# ✅ 試算表與醫師名單
SHEET_URL = "https://docs.google.com/spreadsheets/d/1rtoP3e7D4FPzXDqv0yIOqYE9gwsdmFQSccODkbTZVDs/edit"
DOCTORS = ["王良財", "林大欽", "劉韋廷", "鄭旭智"]

# ✅ 核心函式

def run_generate_night_fee_word():
    book = gc.open_by_url(SHEET_URL)
    all_sheets = book.worksheets()

    now = datetime.now()
    target_month = now.month - 1 or 12
    target_year = now.year if now.month != 1 else now.year - 1

    data_by_doctor = {name: [] for name in DOCTORS}

    for sheet in all_sheets:
        if sheet.title == "使用者對照表":
            continue
        rows = sheet.get_all_records()
        for row in rows:
            timestamp = row.get("時間戳記")
            name = row.get("醫師姓名")
            date_str = row.get("值班日期")
            if name not in DOCTORS or not timestamp or not date_str:
                continue

            ts = datetime.strptime(timestamp, "%Y/%m/%d %H:%M:%S")
            if ts.year == target_year and ts.month == target_month:
                data_by_doctor[name].extend(date_str.split(","))

    # ✅ 開啟樣板並填入資料
    doc = Document("templates/夜點費樣板.docx")
    for para in doc.paragraphs:
        if "{年}" in para.text:
            para.text = para.text.replace("{年}", str(target_year))
        if "{月}" in para.text:
            para.text = para.text.replace("{月}", str(target_month))

    for table in doc.tables:
        for row in table.rows:
            name = row.cells[1].text.strip()
            if name in DOCTORS:
                dates = [d.strip() for d in data_by_doctor[name]]
                row.cells[2].text = ", ".join(dates)
                row.cells[3].text = str(len(dates)) if dates else ""

    # ✅ 儲存檔案
    filename = f"夜點費申請表_{target_year}年{target_month}月.docx"
    filepath = f"/tmp/{filename}"
    doc.save(filepath)

    # ✅ 上傳到 Google Drive
    file_metadata = {
        'name': filename,
        'parents': [FOLDER_ID],
        'mimeType': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    }
    media = MediaFileUpload(filepath, mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
    DRIVE.files().create(body=file_metadata, media_body=media, fields='id').execute()

    return True
