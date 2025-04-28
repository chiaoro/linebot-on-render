import os, json, gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from dotenv import load_dotenv
from utils.line_push import push_text_to_user

load_dotenv()

def run_daily_push():
    SCOPE = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds_dict = json.loads(os.getenv("GOOGLE_CREDENTIALS"))
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
    gc = gspread.authorize(creds)
    sheet = gc.open_by_url(os.getenv("DAILY_PUSH_SHEET_URL")).worksheet("每日推播")
    records = sheet.get_all_records()
    today = datetime.now().strftime("%Y/%m/%d")
    for record in records:
        if record.get("日期") == today and record.get("推播狀態") != "已推播":
            push_text_to_user(record["user_id"], record["訊息內容"])
            sheet.update_cell(records.index(record) + 2, list(records[0].keys()).index("推播狀態") + 1, "已推播")
