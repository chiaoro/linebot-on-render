# utils/schedule_utils.py

import gspread
from datetime import datetime

# ✅ Google Sheets 認證
from utils.google_auth import get_gspread_client

def handle_submission(name, off_days):
    gc = get_gspread_client()
    sheet = gc.open_by_url("https://docs.google.com/spreadsheets/d/1fHf5XlbvLMd6ytAh_t8Bsi5ghToiQHZy1NlVfEG7VIo/edit").worksheet("外科醫師休假登記表")
    today = datetime.now().strftime("%Y/%m/%d")
    sheet.append_row([today, name, off_days])
