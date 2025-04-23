import os, json, gspread
from oauth2client.service_account import ServiceAccountCredentials
from linebot import LineBotApi
from linebot.models import TextSendMessage
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

# ✅ LINE Bot
line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
group_id = os.getenv("All_doctor_group_id")

# ✅ Google Sheets 認證（穩定版）
SCOPE = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds_dict = json.loads(os.environ.get("GOOGLE_CREDENTIALS"))
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
gc = gspread.authorize(creds)






# ✅ 開啟工作表
sheet = gc.open_by_url(
    "https://docs.google.com/spreadsheets/d/1XpX1l7Uf93XWNEYdZsHx-3IXpPf4Sb9Zl0ARGa4Iy5c/edit"
).worksheet("重要會議提醒")

def send_important_event_reminder():
    tomorrow = datetime.now().date() + timedelta(days=1)

    rows = sheet.get_all_records()
    headers = sheet.row_values(1)
    status_col = headers.index("提醒狀態") + 1  # gspread從1開始算

    for i, row in enumerate(rows, start=2):
        date_str = row.get("會議日期", "").strip()
        time_str = row.get("會議時間", "").strip()
        name = row.get("會議名稱", "").strip()
        location = row.get("會議地點", "").strip()
        group_env = row.get("推播對象", "").strip()
        status = row.get("提醒狀態", "").strip()

        # ✅ 日期解析（自動補上今年年份）
        try:
            if "/" in date_str and len(date_str.split("/")[0]) <= 2:
                date_str = f"{datetime.now().year}/{date_str}"  # 補今年年份
            meeting_date = datetime.strptime(date_str, "%Y/%m/%d").date()
        except:
            print(f"❌ 日期格式錯誤：{date_str}")
            continue

        # ✅ 判斷是否推播
        if meeting_date != tomorrow or status == "✅已提醒":
            continue

        group_id = os.getenv(group_env)
        if not group_id:
            print(f"❌ 無法取得群組 ID：{group_env}")
            continue

        weekday_name = ["一", "二", "三", "四", "五", "六", "日"][meeting_date.weekday()]
        message = (
            f"📣【重要會議提醒】\n"
            f"明天（{meeting_date.month}/{meeting_date.day}（{weekday_name}））{time_str} 即將於 {location} 召開 {name}，\n"
            f"請各位準時出席唷。"
        )

        # ✅ 發送推播
        line_bot_api.push_message(group_id, TextSendMessage(text=message))
        print(f"✅ 已推播：{name} ➜ {group_env}")


if __name__ == "__main__":
    send_important_event_reminder()

        

        # ✅ 更新提醒狀態
        sheet.update_cell(i, status_col, "✅已提醒")
