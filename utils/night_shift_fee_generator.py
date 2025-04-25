import os, json
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from docx import Document
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

# ✅ Google Drive API
DRIVE = build('drive', 'v3', credentials=creds)
FOLDER_ID = "1s-joUzZQBHyCKmWZRD4F78qjvvEZ15Dq"  # 雲端目錄 ID

# ✅ Word 樣板對應表
TEMPLATE_MAP = {
    "內科": "templates/內科_樣板.docx",
    "醫療部": "templates/醫療部_樣板.docx"
}

SHEET_URL = "https://docs.google.com/spreadsheets/d/1rtoP3e7D4FPzXDqv0yIOqYE9gwsdmFQSccODkbTZVDs/edit"


def run_generate_night_fee_word():
    book = gc.open_by_url(SHEET_URL)
    worksheets = book.worksheets()

    now = datetime.now()
    target_month = now.month - 1 or 12
    target_year = now.year if now.month != 1 else now.year - 1

    for sheet in worksheets:
        if sheet.title == "使用者對照表":
            continue

        dept = sheet.title
        rows = sheet.get_all_records()

        doctor_data = []

        for row in rows:
            ts_str = row.get("時間戳記")
            name = row.get("醫師姓名")
            dates = row.get("值班日期")

            if not ts_str or not name or not dates:
                continue

            ts = datetime.strptime(ts_str, "%Y/%m/%d %H:%M:%S")
            if ts.year == target_year and ts.month == target_month:
                doctor_data.append({
                    "醫師姓名": name,
                    "值班日期": ", ".join([d.strip() for d in dates.split(",")]),
                    "班數": str(len([d.strip() for d in dates.split(",") if d.strip()]))
                })

        if dept not in TEMPLATE_MAP:
            continue

        # ✅ 使用對應樣板產出 Word
        template_path = TEMPLATE_MAP[dept]
        doc = Document(template_path)

        for para in doc.paragraphs:
            if "{年}" in para.text:
                para.text = para.text.replace("{年}", str(target_year))
            if "{月}" in para.text:
                para.text = para.text.replace("{月}", str(target_month))

        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    text = cell.text
                    for entry in doctor_data:
                        if "{醫師姓名}" in text:
                            cell.text = text.replace("{醫師姓名}", entry["醫師姓名"])
                        if "{值班日期}" in text:
                            cell.text = text.replace("{值班日期}", entry["值班日期"])
                        if "{班數}" in text:
                            cell.text = text.replace("{班數}", entry["班數"])

        filename = f"{dept}_夜點費申請表_{target_year}年{target_month}月.docx"
        filepath = f"/tmp/{filename}"
        doc.save(filepath)

        file_metadata = {
            'name': filename,
            'parents': [FOLDER_ID],
            'mimeType': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        }
        media = MediaFileUpload(filepath, mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        DRIVE.files().create(body=file_metadata, media_body=media, fields='id').execute()

    return True
