import os
import json
from datetime import datetime, timedelta
import gspread
from google.oauth2 import service_account
from linebot import LineBotApi
from linebot.models import TextSendMessage
from dotenv import load_dotenv

load_dotenv()

line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
group_id = os.getenv("All_doctor_group_id")

# ✅ 🔧加上這段才不會錯！
creds_info = json.loads(os.getenv("GOOGLE_CREDENTIALS"))
scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
credentials = service_account.Credentials.from_service_account_info(creds_info, scopes=scopes)
client = gspread.authorize(credentials)

sheet = client.open_by_url(
    "https://docs.google.com/spreadsheets/d/1XpX1l7Uf93XWNEYdZsHx-3IXpPf4Sb9Zl0ARGa4Iy5c/edit"
).worksheet("院務會議請假")

def send_meeting_reminder():
    today = datetime.now().date()
    target_date = today + timedelta(days=5)

    rows = sheet.get_all_records()
    headers = sheet.row_values(1)
    status_col = headers.index("提醒狀態") + 1  # 因為 gspread 是從 1 開始

    for i, row in enumerate(rows, start=2):  # 資料從第2列開始
        date_str = row.get("會議日期")
        time_str = row.get("會議時間")
        name = row.get("會議名稱")
        status = row.get("提醒狀態", "")

        try:
            meeting_date = datetime.strptime(date_str, "%Y/%m/%d").date()
        except Exception:
            continue

        if meeting_date == target_date and status != "✅已提醒":
            weekday = ['一', '二', '三', '四', '五', '六', '日'][meeting_date.weekday()]
            meeting_time = time_str.replace(":", "").zfill(4)
            message = (
                f"🎉 叮咚～小秘來報告！\n"
                f"{meeting_date.month}/{meeting_date.day}（{weekday}）{meeting_time} 的 {name}請假申請已經開放囉～\n"
                f"想請假的朋友可以快快來找我申請唷！💌"
            )

            # ✅ 傳送提醒
            line_bot_api.push_message(group_id, TextSendMessage(text=message))

            # ✅ 更新提醒狀態為「✅已提醒」
            sheet.update_cell(i, status_col, "✅已提醒")
