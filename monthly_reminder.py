import os, json, gspread
from oauth2client.service_account import ServiceAccountCredentials
from linebot import LineBotApi
from linebot.models import TextSendMessage
from datetime import datetime
from dotenv import load_dotenv

# ✅ 載入環境變數
load_dotenv()

# ✅ LINE Bot 初始化
line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))

# ✅ Google Sheets 認證
SCOPE = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds_dict = json.loads(os.environ.get("GOOGLE_CREDENTIALS"))
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
gc = gspread.authorize(creds)

# ✅ 開啟「固定日期推播」分頁
sheet = gc.open_by_url(
    "https://docs.google.com/spreadsheets/d/1XpX1l7Uf93XWNEYdZsHx-3IXpPf4Sb9Zl0ARGa4Iy5c/edit"
).worksheet("固定日期推播")

def send_monthly_fixed_reminders():
    today = datetime.now().day
    rows = sheet.get_all_records()
    headers = sheet.row_values(1)
    status_col = headers.index("提醒狀態") + 1  # gspread 是從 1 開始

    for i, row in enumerate(rows, start=2):  # 從第 2 列開始是資料
        try:
            target_day = int(row.get("日期", 0))
        except:
            continue

        item = row.get("推播項目", "").strip()
        env_key = row.get("推播對象", "").strip()
        status = row.get("提醒狀態", "").strip()

        # ➜ 條件：今天是指定日，且尚未提醒
        if today != target_day or status == "✅已提醒":
            continue

        # ➜ 從環境變數取得群組 ID
        group_id = os.getenv(env_key)
        if not group_id:
            print(f"❌ 找不到對應的環境變數：{env_key}，略過")
            continue

        # ✅ 組合訊息內容
        if item == "申請夜點費":
            message = (
                "📣 各位值班英雄辛苦啦～\n"
                "今天是每月 1 號，別忘了申請夜點費唷！\n"
                "需要協助請隨時呼叫小秘～"
            )
        elif item == "申請休假單":
            message = (
                "📝 親愛的醫師您好：\n"
                "今天是每月 1 號，請記得填寫本月的休假申請單！\n"
                "👉 表單連結：https://docs.google.com/forms/d/e/1FAIpQLScT2xDChXI7jBVPAf0rzKmtTXXtbZ6JFFD7EGfhmAvwSVfYzQ/viewform?usp=sharing\n"
                "如已完成可忽略此訊息，謝謝您～"
            )
        else:
            message = f"📌 今天是每月 {target_day} 號，別忘了：{item}"

        # ✅ 發送 LINE 推播
        try:
            line_bot_api.push_message(group_id, TextSendMessage(text=message))
            print(f"✅ 推播完成：{item} ➜ {env_key}")
            sheet.update_cell(i, status_col, "✅已提醒")
        except Exception as e:
            print(f"❌ 推播失敗：{item} ➜ {env_key}，錯誤：{e}")
