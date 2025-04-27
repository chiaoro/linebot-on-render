import os, json, gspread
from oauth2client.service_account import ServiceAccountCredentials
from linebot import LineBotApi
from linebot.models import TextSendMessage
from datetime import datetime, timedelta
from dotenv import load_dotenv

# ✅ 載入環境變數
load_dotenv()

# ✅ LINE Bot 設定
line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))

# ✅ Google Sheets 認證
SCOPE = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds_dict = json.loads(os.environ.get("GOOGLE_CREDENTIALS"))
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
gc = gspread.authorize(creds)

# ✅ 開啟「重要會議提醒」工作表
sheet = gc.open_by_url(
    "https://docs.google.com/spreadsheets/d/1XpX1l7Uf93XWNEYdZsHx-3IXpPf4Sb9Zl0ARGa4Iy5c/edit"
).worksheet("重要會議提醒")

def send_important_event_reminder():
    tomorrow = datetime.now().date() + timedelta(days=1)
    rows = sheet.get_all_records()
    headers = sheet.row_values(1)
    status_col = headers.index("提醒狀態") + 1  # gspread從1開始算欄位

    print(f"▶️ 明天日期：{tomorrow}")

    for i, row in enumerate(rows, start=2):  # 從第2列開始（跳過標題）
        date_str = row.get("會議日期", "").strip()
        time_str = row.get("會議時間", "").strip()
        name = row.get("會議名稱", "").strip()
        location = row.get("會議地點", "").strip()
        group_env = row.get("推播對象", "").strip()
        status = row.get("提醒狀態", "").strip()

        print(f"➡️ 處理第 {i} 列：{date_str} {time_str} {name} ({group_env}) 狀態：{status or '空白'}")

        # 解析會議日期
        try:
            if "/" in date_str and len(date_str.split("/")[0]) <= 2:
                date_str = f"{datetime.now().year}/{date_str}"
            meeting_date = datetime.strptime(date_str, "%Y/%m/%d").date()
        except Exception as e:
            print(f"❌ 日期格式錯誤，跳過：{date_str}，錯誤訊息：{e}")
            continue

        if meeting_date != tomorrow:
            print(f"⏭️ 日期不是明天({tomorrow})，跳過")
            continue

        if status == "✅已提醒":
            print(f"⏭️ 已提醒過，跳過")
            continue

        group_id = os.getenv(group_env)
        if not group_id:
            print(f"❌ 無法取得群組 ID：{group_env}，跳過")
            continue

        weekday_name = ["一", "二", "三", "四", "五", "六", "日"][meeting_date.weekday()]
        message = (
            f"📣【重要會議提醒】\n"
            f"明天（{meeting_date.month}/{meeting_date.day}（{weekday_name}））{time_str} 即將於 {location} 召開《{name}》，\n"
            f"請各位準時出席唷。"
        )

        try:
            line_bot_api.push_message(group_id, TextSendMessage(text=message))
            print(f"✅ 成功推播 ➜ {group_env} ：{name}")
            sheet.update_cell(i, status_col, "✅已提醒")
        except Exception as e:
            print(f"❌ 推播失敗：{e}")

# ✅ 若直接執行，就跑一次推播
if __name__ == "__main__":
    send_important_event_reminder()
