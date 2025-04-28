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

# ✅ Google Sheets 認證
SCOPE = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds_dict = json.loads(os.environ.get("GOOGLE_CREDENTIALS"))
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
gc = gspread.authorize(creds)

# ✅ 開啟院務會議請假分頁
sheet = gc.open_by_url(
    "https://docs.google.com/spreadsheets/d/1XpX1l7Uf93XWNEYdZsHx-3IXpPf4Sb9Zl0ARGa4Iy5c/edit"
).worksheet("院務會議請假")

def send_meeting_reminder():
    today = datetime.now().date()
    print(f"🛎️ send_meeting_reminder() 被觸發了！今天是 {today}")
    print(f"🎯 推播目標群組ID：{group_id}")

    start_date = today + timedelta(days=3)
    end_date = today + timedelta(days=7)
    print(f"🗓️ 設定提醒範圍是：{start_date} ～ {end_date}")

    rows = sheet.get_all_records()
    headers = sheet.row_values(1)
    status_col = headers.index("提醒狀態") + 1  # gspread從1開始

    found = False

    for i, row in enumerate(rows, start=2):
        date_str = row.get("會議日期")
        time_str = row.get("會議時間")
        name = row.get("會議名稱")
        status = row.get("提醒狀態", "")

        if not date_str:
            print(f"⚠️ 第{i}列會議日期為空，略過。")
            continue

        try:
            meeting_date = datetime.strptime(date_str, "%Y/%m/%d").date()
            print(f"📅 讀到會議：{meeting_date} {name} (提醒狀態：{status})")
        except Exception as e:
            print(f"❌ 日期解析失敗：{date_str}，錯誤訊息：{e}")
            continue

        # ✅ 判斷是否在提醒範圍內
        if start_date <= meeting_date <= end_date and status != "✅已提醒":
            print(f"✅ {meeting_date} 的 {name} 在提醒範圍內！準備推播！")
            weekday = ['一', '二', '三', '四', '五', '六', '日'][meeting_date.weekday()]
            meeting_time = time_str.replace(":", "").zfill(4)
            message = (
                f"🎉 叮咚～小秘來報告！\n"
                f"{meeting_date.month}/{meeting_date.day}（{weekday}）{meeting_time} 的 {name}請假申請已經開放囉～\n"
                f"想請假的朋友可以快快來找我申請唷！💌"
            )

            # ✅ 推播
            try:
                line_bot_api.push_message(group_id, TextSendMessage(text=message))
                print(f"✅ 成功推播訊息到群組！內容是：{message}")
            except Exception as e:
                print(f"❌ 推播失敗：{e}")
                continue

            # ✅ 更新提醒狀態
            try:
                sheet.update_cell(i, status_col, "✅已提醒")
                print(f"✅ 更新第{i}列提醒狀態成功（{name}）")
            except Exception as e:
                print(f"❌ 更新提醒狀態失敗：{e}")

            found = True

    if not found:
        print("⚠️ 今天沒有符合提醒條件的院務會議。")

