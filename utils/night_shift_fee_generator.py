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
    "醫療部": "templates/醫療部_樣板.docx",
    "外科": "templates/外科_樣板.docx"
}

SHEET_URL = "https://docs.google.com/spreadsheets/d/1rtoP3e7D4FPzXDqv0yIOqYE9gwsdmFQSccODkbTZVDs/edit"


def run_generate_night_fee_word():
    book = gc.open_by_url(SHEET_URL)
    worksheets = book.worksheets()

    now = datetime.now()
    target_month = now.month - 1 if now.month != 1 else 12
    target_year = now.year if now.month != 1 else now.year - 1

    for sheet in worksheets:
        if sheet.title == "使用者對照表":
            continue

        dept = sheet.title
        rows = sheet.get_all_records()

        doctor_data = []

        for row in rows:
            name = row.get("醫師姓名")
            dates = row.get("值班日期")

            if not name or not dates:
                continue

            # ✅ 將每個值班日期取出來判斷是不是上個月
            date_list = [d.strip() for d in dates.split(",") if d.strip()]
            filtered_dates = []

            for date_str in date_list:
                try:
                    # 處理日期格式，例如 "4/5" 補上今年年份
                    if "/" in date_str and len(date_str.split("/")[0]) <= 2:
                        date_str_full = f"{now.year}/{date_str}"
                    else:
                        date_str_full = date_str

                    duty_date = datetime.strptime(date_str_full, "%Y/%m/%d")

                    # 判斷是不是目標年月
                    if duty_date.year == target_year and duty_date.month == target_month:
                        filtered_dates.append(f"{duty_date.month}/{duty_date.day}")
                except Exception as e:
                    print(f"❌ 日期格式錯誤：{date_str}，錯誤訊息：{e}")
                    continue

            if filtered_dates:
                doctor_data.append({
                    "醫師姓名": name,
                    "值班日期": ", ".join(filtered_dates),
                    "班數": str(len(filtered_dates))
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
                    for entry in doctor_data:
                        if "{醫師姓名}" in cell.text:
                            cell.text = cell.text.replace("{醫師姓名}", entry["醫師姓名"])
                        if "{值班日期}" in cell.text:
                            cell.text = cell.text.replace("{值班日期}", entry["值班日期"])
                        if "{班數}" in cell.text:
                            cell.text = cell.text.replace("{班數}", entry["班數"])

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
