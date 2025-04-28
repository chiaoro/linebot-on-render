# meeting_reminder.py
import os, json
from datetime import datetime, timedelta
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv
from linebot import LineBotApi
from linebot.models import TextSendMessage

load_dotenv()

LINE_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
GROUP_ID = os.getenv("All_doctor_group_id")

line_bot_api = LineBotApi(LINE_TOKEN)

# Google Sheets 認證
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
CREDS_DICT = json.loads(os.getenv("GOOGLE_CREDENTIALS"))
CREDS = ServiceAccountCredentials.from_json_keyfile_dict(CREDS_DICT, SCOPE)
GC = gspread.authorize(CREDS)

# 院務會議請假推播設定
SHEET_URL = os.getenv("MEETING_SHEET_URL", "https://docs.google.com/spreadsheets/d/.../edit")
WORKSHEET_NAME = os.getenv("MEETING_WORKSHEET_NAME", "院務會議請假")

def run_meeting_reminder():
    """推播院務會議請假提醒 (3~5 天前)"""
    sheet = GC.open_by_url(SHEET_URL).worksheet(WORKSHEET_NAME)
    records = sheet.get_all_records()
    today = datetime.now().date()
    for rec in records:
        date_str = rec.get("會議日期") or rec.get("日期")
        try:
            meeting_date = datetime.strptime(date_str, "%Y/%m/%d").date()
        except:
            continue
        days_diff = (meeting_date - today).days
        if 3 <= days_diff <= 5:
            text = f"📣【會議請假提醒】 {meeting_date.strftime('%Y/%m/%d')}（{meeting_date.strftime('%A')}） 請記得請假並排除工作行程。"
            line_bot_api.push_message(GROUP_ID, TextSendMessage(text=text))


# monthly_reminder.py
import os, json
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv
from linebot import LineBotApi
from linebot.models import TextSendMessage

load_dotenv()

LINE_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
GROUP_ID = os.getenv("All_doctor_group_id")

line_bot_api = LineBotApi(LINE_TOKEN)

# Google Sheets 認證
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
CREDS_DICT = json.loads(os.getenv("GOOGLE_CREDENTIALS"))
CREDS = ServiceAccountCredentials.from_json_keyfile_dict(CREDS_DICT, SCOPE)
GC = gspread.authorize(CREDS)

# 固定日期推播設定
SHEET_URL = os.getenv("MONTHLY_SHEET_URL", "https://docs.google.com/spreadsheets/d/.../edit")
WORKSHEET_NAME = os.getenv("MONTHLY_WORKSHEET_NAME", "固定日期推播")

def run_monthly_reminder():
    """每日檢查固定日期推播 (當日符合)"""
    sheet = GC.open_by_url(SHEET_URL).worksheet(WORKSHEET_NAME)
    records = sheet.get_all_records()
    today_str = datetime.now().strftime("%Y/%m/%d")
    status_col = list(records[0].keys()).index("提醒狀態") + 1
    for idx, rec in enumerate(records, start=2):
        if rec.get("日期") == today_str and rec.get("提醒狀態") != "已提醒":
            content = rec.get("推播項目")
            line_bot_api.push_message(GROUP_ID, TextSendMessage(text=f"{today_str} {content}"))
            sheet.update_cell(idx, status_col, "已提醒")


# event_reminder.py
import os, json
from datetime import datetime, timedelta
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv
from linebot import LineBotApi
from linebot.models import TextSendMessage

load_dotenv()

LINE_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
GROUP_ID = os.getenv("All_doctor_group_id")

line_bot_api = LineBotApi(LINE_TOKEN)

# Google Sheets 認證
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
CREDS_DICT = json.loads(os.getenv("GOOGLE_CREDENTIALS"))
CREDS = ServiceAccountCredentials.from_json_keyfile_dict(CREDS_DICT, SCOPE)
GC = gspread.authorize(CREDS)

# 重要會議提醒設定
SHEET_URL = os.getenv("EVENT_SHEET_URL", "https://docs.google.com/spreadsheets/d/.../edit")
WORKSHEET_NAME = os.getenv("EVENT_WORKSHEET_NAME", "重要會議提醒")

WEEKDAY_MAP = {0:"星期一",1:"星期二",2:"星期三",3:"星期四",4:"星期五",5:"星期六",6:"星期日"}

def run_event_reminder():
    """推播明日重要會議提醒"""
    sheet = GC.open_by_url(SHEET_URL).worksheet(WORKSHEET_NAME)
    records = sheet.get_all_records()
    tomorrow = datetime.now().date() + timedelta(days=1)
    for rec in records:
        date_str = rec.get("會議日期") or rec.get("日期")
        try:
            event_date = datetime.strptime(date_str, "%Y/%m/%d").date()
        except:
            continue
        if event_date == tomorrow:
            weekday = WEEKDAY_MAP[event_date.weekday()]
            time = rec.get("會議時間", "")
            location = rec.get("會議地點", "")
            title = rec.get("會議名稱") or rec.get("會議主題")
            text = f"📣【重要會議提醒】 明天({event_date.strftime('%Y/%m/%d')}) {weekday} {time} 即將於{location}召開{title}，請各位準時出席唷。"
            line_bot_api.push_message(GROUP_ID, TextSendMessage(text=text))
