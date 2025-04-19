import os
import json
from datetime import datetime
import gspread
from google.oauth2 import service_account
from linebot import LineBotApi
from linebot.models import TextSendMessage
from dotenv import load_dotenv

load_dotenv()

# ✅ 初始化 LINE Bot
line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))

# ✅ 初始化 Google Sheets 認證
creds_info = json.loads(os.getenv("GOOGLE_CREDENTIALS"))
credentials = service_account.Credentials.from_service_account_info(creds_info)
client = gspread.authorize(credentials)

# ✅ 讀取固定日期推播分頁
sheet = client.open_by_url(
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

        # ➜ 組合訊息內容（你可以在這裡加更多 if 分類）
        if item == "申請夜點費":
            message = (
                "📣 各位值班英雄辛苦啦～\n"
                "今天是每月 1 號，別忘了申請夜點費唷！\n"
                "需要協助請隨時呼叫小秘～"
            )
        else:
            message = f"📌 今天是每月 {target_day} 號，別忘了：{item}"

        # ✅ 發送 LINE 推播
        line_bot_api.push_message(group_id, TextSendMessage(text=message))
        print(f"✅ 推播完成：{item} ➜ {env_key}")

        # ✅ 更新狀態為已提醒
        sheet.update_cell(i, status_col, "✅已提醒")
