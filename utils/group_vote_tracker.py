# ✅ 升級版 group_vote_tracker.py - 支援跨天群組統計記錄至 Google Sheets

import re
from datetime import datetime
import gspread
import os, json
from oauth2client.service_account import ServiceAccountCredentials
from linebot.models import TextSendMessage

# ✅ 初始化 Google Sheets 連線
SCOPE = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds_dict = json.loads(os.environ.get("GOOGLE_CREDENTIALS"))
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
gc = gspread.authorize(creds)

STAT_SHEET_URL = "https://docs.google.com/spreadsheets/d/14TdjFoBVJITE6_lEaGj32NT8S3o-Ysk8ObstdpNxLOI/edit"
MAPPING_SHEET_URL = "https://docs.google.com/spreadsheets/d/1fHf5XlbvLMd6ytAh_t8Bsi5ghToiQHZy1NlVfEG7VIo/edit"

# ✅ 群組統計暫存記憶體
vote_sessions = {}  # group_id: {"sheet_name": str, "votes": {user_id: count}}

# ✅ 從使用者對照表取得暱稱
def get_user_display_name(user_id):
    try:
        sheet = gc.open_by_url(MAPPING_SHEET_URL).worksheet("UserMapping")
        rows = sheet.get_all_records()
        for row in rows:
            if row.get("LINE_USER_ID") == user_id:
                return row.get("使用者暱稱", "未知")
    except:
        pass
    return "未知"

# ✅ 建立唯一分頁名稱：日期_群組名稱(可編號)
def get_unique_sheet_name(group_name):
    today = datetime.now().strftime("%Y-%m-%d")
    base_name = f"{today}_{group_name}"
    sheet = gc.open_by_url(STAT_SHEET_URL)
    existing_titles = [ws.title for ws in sheet.worksheets()]
    if base_name not in existing_titles:
        return base_name
    else:
        idx = 1
        while f"{base_name}({idx})" in existing_titles:
            idx += 1
        return f"{base_name}({idx})"

# ✅ 主功能：處理統計訊息
def handle_group_vote(event, line_bot_api):
    user_msg = event.message.text.strip()
    text = user_msg.replace("【", "").replace("】", "").strip()

    if event.source.type != "group":
        return False

    group_id = event.source.group_id
    user_id = event.source.user_id
    display_name = get_user_display_name(user_id)

    group_name = os.getenv(group_id, group_id)  # 若無對應名稱則用 ID

    # ✅ 開啟統計
    if text == "開啟統計":
        sheet_name = get_unique_sheet_name(group_name)
        vote_sessions[group_id] = {"sheet_name": sheet_name, "votes": {}}
        sheet = gc.open_by_url(STAT_SHEET_URL)
        sheet.add_worksheet(title=sheet_name, rows=100, cols=5)
        ws = sheet.worksheet(sheet_name)
        ws.append_row(["統計時間", "ID", "使用者暱稱", "數量", "累加數量"])
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"🟢 統計已開啟，紀錄於分頁：{sheet_name}"))
        return True

    # ✅ 結束統計
    if text == "結束統計":
        if group_id in vote_sessions:
            votes = vote_sessions[group_id]["votes"]
            total = sum(votes.values())
            del vote_sessions[group_id]
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"🔴 統計結束，本場總人數：{total} 人 🙌"))
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="⚠️ 尚未開啟統計功能。"))
        return True

    # ✅ 查詢目前人數
    if text == "統計人數":
        if group_id in vote_sessions:
            total = sum(vote_sessions[group_id]["votes"].values())
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"📊 目前累計 {total} 人"))
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="⚠️ 尚未開啟統計功能。"))
        return True

    # ✅ 加票 +1 ~ +99
    if group_id in vote_sessions:
        plus_match = re.match(r"^\+(\d+)$", text)
        if plus_match:
            count = int(plus_match.group(1))
            votes = vote_sessions[group_id]["votes"]
            prev = votes.get(user_id, 0)
            votes[user_id] = prev + count

            # ✅ 寫入試算表
            sheet = gc.open_by_url(STAT_SHEET_URL)
            ws = sheet.worksheet(vote_sessions[group_id]["sheet_name"])
            ws.append_row([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                user_id,
                display_name,
                count,
                votes[user_id]
            ])
            return True

        elif text == "-1":
            votes = vote_sessions[group_id]["votes"]
            if user_id in votes and votes[user_id] > 0:
                votes[user_id] -= 1
                sheet = gc.open_by_url(STAT_SHEET_URL)
                ws = sheet.worksheet(vote_sessions[group_id]["sheet_name"])
                ws.append_row([
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    user_id,
                    display_name,
                    -1,
                    votes[user_id]
                ])
            return True

    return False
