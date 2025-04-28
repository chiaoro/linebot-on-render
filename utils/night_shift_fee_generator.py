# utils/night_shift_fee_generator.py
import os, json
from datetime import date, timedelta
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from docx import Document
from io import BytesIO
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from utils.line_push_utils import push_text_to_group

# Google Sheets & Drive 認證
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
CREDS_DICT = json.loads(os.getenv("GOOGLE_CREDENTIALS"))
CREDS = ServiceAccountCredentials.from_json_keyfile_dict(CREDS_DICT, SCOPE)
GC = gspread.authorize(CREDS)
DRIVE = build('drive', 'v3', credentials=CREDS)

SHEET_URL = os.getenv("NIGHT_FEE_SHEET_URL")
WORKSHEET_NAME = os.getenv("NIGHT_FEE_WORKSHEET_NAME", "夜點費申請")
TEMPLATE_DOC_ID = os.getenv("NIGHT_FEE_TEMPLATE_ID")
FOLDER_ID = os.getenv("NIGHT_FEE_OUTPUT_FOLDER_ID")
GROUP_ID = os.getenv("surgery_group_id") or os.getenv("All_doctor_group_id")


def generate_night_fee_doc():
    """根據上月夜點費申請資料生成 Word 報表並上傳至 Google Drive"""
    sheet = GC.open_by_url(SHEET_URL).worksheet(WORKSHEET_NAME)
    records = sheet.get_all_records()
    today = date.today()
    last_month = today.replace(day=1) - timedelta(days=1)
    # 篩選上月申請資料
    filtered = [r for r in records if datetime.strptime(r['時間'], '%Y/%m/%d %H:%M:%S').month == last_month.month]
    # 載入範本文件
    template = DRIVE.files().export_media(fileId=TEMPLATE_DOC_ID, mimeType='application/vnd.openxmlformats-officedocument.wordprocessingml.document').execute()
    doc = Document(BytesIO(template))
    table = doc.add_table(rows=1, cols=3)
    hdr = table.rows[0].cells
    hdr[0].text, hdr[1].text, hdr[2].text = '醫師', '申請時間', '狀態'
    for r in filtered:
        cells = table.add_row().cells
        cells[0].text = r['醫師姓名']
        cells[1].text = r['時間']
        cells[2].text = r['提醒狀態']
    output = BytesIO()
    doc.save(output)
    output.seek(0)
    fname = f"夜點費_{last_month.strftime('%Y%m')}.docx"
    media = MediaIoBaseUpload(output, mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
    file = DRIVE.files().create(body={'name': fname, 'parents': [FOLDER_ID]}, media_body=media, fields='id, webViewLink').execute()
    url = file.get('webViewLink')
    push_text_to_group(GROUP_ID, f"上月夜點費報表已生成：{url}")
    return url
