# handlers/stats_handler.py

import re
from datetime import datetime
from linebot.models import TextSendMessage
from utils.gspread_client import get_gspread_client

# 統計資料暫存，用來記錄每個人的累加量
attendance_data = {
    "active": False,
    "records": {}  # user_id: {"name": xxx, "count": x}
}

def log_stat_to_sheet(user_id, user_name, value):
    # ✅ 設定試算表與分頁
    SPREADSHEET_ID = "14TdjFoBVJITE6_lEaGj32NT8S3o-Ysk8ObstdpNxLOI"
    SHEET_NAME = "統計紀錄"

    client = get_gspread_client()
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)

    now = datetime.now()
    time_str = now.strftime("%Y/%m/%d %H:%M:%S")

    current_total = attendance_data["records"].get(user_id, {}).get("count", 0)

    row = [
        time_str,        # 統計時間
        user_id,         # ID
        user_name,       # 使用者暱稱
        value,           # 本次變動數量（+1 / -1）
        current_total    # 累加數量
    ]
    sheet.append_row(row, value_input_option="USER_ENTERED")


def handle_stats(event, user_id, text, line_bot_api, user_name="未知使用者"):
    text = text.strip()
    reply_token = event.reply_token

    # ✅ 開啟統計
    if text == "開啟統計":
        attendance_data["active"] = True
        attendance_data["records"] = {}
        line_bot_api.reply_message(
            reply_token,
            TextSendMessage("🟢 統計功能已開啟！請大家輸入 +1 / -1")
        )
        return True

    # ✅ 結束統計
    if text == "結束統計":
        if not attendance_data["active"]:
            line_bot_api.reply_message(reply_token, TextSendMessage("⚠️ 尚未開啟統計功能"))
            return True
    
        total = sum(
            record["count"] for record in attendance_data["records"].values()
            if record["count"] != 0
        )
    
        result_text = f"🔴 統計已結束：\n\n👥 總人數為：{total}人 🙌"
    
        line_bot_api.reply_message(reply_token, TextSendMessage(result_text))
        attendance_data["active"] = False
        return True

    # ✅ 處理 +1 / -1 類訊息並寫入 Sheet
    if attendance_data["active"]:
        match = re.match(r"^([+-])(\d+)$", text)
        if match:
            sign, number = match.groups()
            count = int(number)
            if sign == "-":
                count *= -1

            # 更新累計
            if user_id not in attendance_data["records"]:
                attendance_data["records"][user_id] = {"name": user_name, "count": 0}
            attendance_data["records"][user_id]["count"] += count

            # 寫入 Google Sheet
            log_stat_to_sheet(user_id, user_name, count)
            return True

    return False
