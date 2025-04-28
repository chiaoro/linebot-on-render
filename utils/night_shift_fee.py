# utils/night_shift_fee.py

from linebot.models import TextSendMessage
import os, json, gspread
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv

load_dotenv()

user_night_fee_sessions = {}

# Google Sheets 認證
SCOPE = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds_dict = json.loads(os.getenv("GOOGLE_CREDENTIALS"))
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
gc = gspread.authorize(creds)

# 夜點費登記表網址
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1rtoP3e7D4FPzXDqv0yIOqYE9gwsdmFQSccODkbTZVDs/edit"
sheet = gc.open_by_url(SPREADSHEET_URL)
worksheet = sheet.worksheet("醫療部")

# 處理夜點費申請
def handle_night_shift_request(user_id, user_msg):
    if user_msg == "夜點費申請":
        user_night_fee_sessions[user_id] = {"step": 1}
        return "📝 請問要申請的值班是哪一天？（例如 5/6 上午）"
    return None

# 繼續處理夜點費申請（第二步）
def continue_night_shift_fee_request(user_id, user_msg):
    if user_id not in user_night_fee_sessions:
        return None

    session = user_night_fee_sessions[user_id]
    step = session["step"]

    if step == 1:
        session["date"] = user_msg
        session["step"] = 2
        return "📝 請問值班班別是？（例如 內科急診白班）"
    elif step == 2:
        session["shift"] = user_msg
        session["step"] = 3
        return "📝 請問值班醫師姓名？"


# 繼續處理夜點費申請（第三步）
def finalize_night_shift_fee_request(user_id, user_msg):
    if user_id not in user_night_fee_sessions:
        return None

    session = user_night_fee_sessions[user_id]
    step = session["step"]

    if step == 3:
        session["doctor_name"] = user_msg

        # 填入 Google Sheets
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        data_row = [
            now,
            session["doctor_name"],
            session["date"],
            session["shift"],
            "已填寫"
        ]
        worksheet.append_row(data_row)

        # 清除暫存
        del user_night_fee_sessions[user_id]

        return f"""✅ 夜點費申請完成！
- 醫師：{data_row[1]}
- 日期：{data_row[2]}
- 班別：{data_row[3]}
"""
    return None

