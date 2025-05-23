#


import os, json, gspread
from dotenv import load_dotenv
from oauth2client.service_account import ServiceAccountCredentials
from utils.line_push import push_text_to_group

load_dotenv()

def send_meeting_reminder():
    SCOPE = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds_dict = json.loads(os.getenv("GOOGLE_CREDENTIALS"))
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
    gc = gspread.authorize(creds)
    sheet = gc.open_by_url(os.getenv("MEETING_REMINDER_SHEET_URL")).worksheet("院務會議請假")
    records = sheet.get_all_records()
    push_text_to_group(os.getenv("All_doctor_group_id"), "📣 請記得回覆本週院務會議出席狀況喔！")
