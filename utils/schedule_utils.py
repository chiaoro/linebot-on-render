# utils/schedule_utils.py

import gspread
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials
import os, json
from dotenv import load_dotenv

load_dotenv()

SCOPE = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
CREDS_DICT = json.loads(os.getenv("GOOGLE_CREDENTIALS"))
CREDS = ServiceAccountCredentials.from_json_keyfile_dict(CREDS_DICT, SCOPE)
GC = gspread.authorize(CREDS)


# 使用者對照表（固定網址）
MAPPING_SHEET_URL = "https://docs.google.com/spreadsheets/d/1fHf5XlbvLMd6ytAh_t8Bsi5ghToiQHZy1NlVfEG7VIo/edit"


# ✅ Google Sheets 認證
from utils.google_auth import get_gspread_client

def handle_submission(name, off_days):
    """接收醫師請假表單，處理並記錄"""
    doc = GC.open_by_url(MAPPING_SHEET_URL)
    sheet = doc.worksheet("排班表")  # 你可以換成要寫入的分頁名稱

    values = [name] + off_days
    sheet.append_row(values)
