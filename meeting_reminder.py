import os
from datetime import datetime, timedelta
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from linebot import LineBotApi
from linebot.models import TextSendMessage
from dotenv import load_dotenv

load_dotenv()

# ✅初始化 LINE Bot
line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
group_id = os.getenv("All_doctor_group_id")  # ✅ 傳給全醫師群組

# ✅初始化 gspread
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name(os.getenv("GOOGLE_CREDENTIALS_FILE"), scope)
client = gspread.authorize(creds)
sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/1XpX1l7Uf93XWNEYdZsHx-3IXpPf4Sb9Zl0ARGa4Iy5c/edit").worksheet("院務會議請假")

def send_meeting_reminder():
    today = datetime.now().date()
    target_date = today + timedelta(days=5)

    rows = sheet.get_all_records()
    for row in rows:
        date_str = row.get("會議日期")
        time_str = row.get("會議時間")
        name = row.get("會議名稱")

        try:
            meeting_date = datetime.strptime(date_str, "%Y/%m/%d").date()
        except Exception:
            continue  # 忽略格式錯誤的列

        if meeting_date == target_date:
            weekday = ['一', '二', '三', '四', '五', '六', '日'][meeting_date.weekday()]
            meeting_time = time_str.replace(":", "").zfill(4)  # 轉為 0730 形式
            message = (
                f"🎉 叮咚～小秘來報告！\n"
                f"{meeting_date.month}/{meeting_date.day}（{weekday}）{meeting_time} 的 {name}請假申請已經開放囉～\n"
                f"想請假的朋友可以快快來找我申請唷！💌"
            )
            line_bot_api.push_message(group_id, TextSendMessage(text=message))
