#✅推播模組

import os
import json
import gspread
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv
from line_push_utils import push_to_doctor

load_dotenv()

def run_daily_push():
    # ✅ Google Sheets 認證
    SCOPE = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds_dict = json.loads(os.environ.get("GOOGLE_CREDENTIALS"))
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
    gc = gspread.authorize(creds)

    # ✅ 開啟推播任務表
    sheet = gc.open_by_url("https://docs.google.com/spreadsheets/d/1FspUjkRckA1g4bYESb7QEUKl1FzOcL5BejhOqkMD0Po/edit")
    worksheet = sheet.worksheet("每日推播")
    data = worksheet.get_all_records()

    # ✅ 比對今天日期
    today_str = datetime.now().strftime("%Y/%m/%d")
    weekday_map = ["一", "二", "三", "四", "五", "六", "日"]

    for idx, row in enumerate(data):
        if row["日期"] != today_str or row["推播狀態"] == "已推播":
            continue

        name = row["醫師姓名"]
        type_ = row["類型"]
        time = row.get("時間", "")
        place = row.get("地點", "")
        content = row.get("通知內容", "")
        weekday = weekday_map[datetime.now().weekday()]

        # 📌 設定訊息格式
        if type_ == "會議":
            message = f"📣 您好，提醒您 {today_str} ({weekday}) {time} {place} 有 {content}，請務必記得出席～"
        elif type_ == "要假單":
            message = (
                "📣 您好，記得盡快完成要假單填寫唷～\n"
                "填寫連結：https://docs.google.com/forms/d/e/1FAIpQLScT2xDChXI7jBVPAf0rzKmtTXXtbZ6JFFD7EGfhmAvwSVfYzQ/viewform?usp=sharing"
            )
        else:
            print(f"⚠️ 類型尚未支援：{type_}")
            continue

        # ✅ 推播
        push_to_doctor(name, message)

        # ✅ 更新「推播狀態」為已推播
        worksheet.update_cell(idx + 2, list(row.keys()).index("推播狀態") + 1, "已推播")

