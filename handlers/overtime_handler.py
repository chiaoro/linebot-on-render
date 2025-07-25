from linebot.models import TextSendMessage, FlexSendMessage
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime
import os
import json

# === 使用者狀態管理 ===
from utils.session_manager import get_session, set_session, clear_session

# ✅ Google Sheets 設定
OVERTIME_SHEET_ID = "1pb5calRrKlCWx16XENcit85pF0qLoH1lvMfGI_WZ_n8"  # 加班申請表
USER_MAPPING_SHEET_ID = "1fHf5XlbvLMd6ytAh_t8Bsi5ghToiQHZy1NlVfEG7VIo"  # 使用者對照表
SERVICE_ACCOUNT_JSON = json.loads(os.getenv("GOOGLE_CREDENTIALS"))

# ✅ 建立 Google Sheets Service
def get_sheets_service():
    creds = service_account.Credentials.from_service_account_info(
        SERVICE_ACCOUNT_JSON,
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    return build("sheets", "v4", credentials=creds).spreadsheets()

# ✅ 從 UserMapping 找醫師姓名
def get_doctor_name_by_user_id(user_id):
    service = get_sheets_service()
    result = service.values().get(
        spreadsheetId=USER_MAPPING_SHEET_ID,
        range="UserMapping!A:B"  # A 欄 user_id，B 欄 醫師姓名
    ).execute()
    values = result.get("values", [])

    for row in values:
        if len(row) >= 2 and row[0] == user_id:
            return row[1]
    return "未知醫師"

# ✅ 寫入 Google Sheet
def save_overtime_to_sheet(user_id, date, time_range, reason):
    doctor_name = get_doctor_name_by_user_id(user_id)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    service = get_sheets_service()
    service.values().append(
        spreadsheetId=OVERTIME_SHEET_ID,
        range="加班申請!A:E",
        valueInputOption="RAW",
        body={
            "values": [[
                now,
                doctor_name,
                date,
                time_range,
                reason
            ]]
        }
    ).execute()


# === 主流程 ===
def handle_overtime(event, user_id, text, line_bot_api):
    # ✅ 判斷是否啟動加班申請
    if text == "加班申請":
        set_session(user_id, {"step": 0, "type": "overtime"})
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="請輸入加班日期（格式：YYYY-MM-DD）")
        )
        return True

    # ✅ 檢查是否在流程中
    session = get_session(user_id)
    if not session or session.get("type") != "overtime":
        return False

    step = session.get("step", 0)

    # Step 0: 日期
    if step == 0:
        session["date"] = text
        session["step"] = 1
        set_session(user_id, session)
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="請輸入加班時間（格式：HH:MM-HH:MM）")
        )
        return True

    # Step 1: 時間
    if step == 1:
        session["time"] = text
        session["step"] = 2
        set_session(user_id, session)
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="請輸入加班事由(需詳述,例如開了什麼刀、完成哪幾份病歷、查哪幾間房等等)")
        )
        return True

    # Step 2: 事由 → 顯示確認 Flex
    if step == 2:
        session["reason"] = text
        session["step"] = 3
        set_session(user_id, session)

        flex_message = {
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {"type": "text", "text": "📋 請確認加班申請", "weight": "bold", "size": "lg", "margin": "md"},
                    {"type": "separator", "margin": "md"},
                    {"type": "box", "layout": "vertical", "margin": "md", "spacing": "sm",
                     "contents": [
                         {"type": "text", "text": f"日期：{session['date']}", "size": "md"},
                         {"type": "text", "text": f"時間：{session['time']}", "size": "md"},
                         {"type": "text", "text": f"事由：{session['reason']}", "size": "md"}
                     ]},
                    {"type": "separator", "margin": "md"},
                    {"type": "box", "layout": "horizontal", "spacing": "md", "margin": "md",
                     "contents": [
                         {"type": "button", "style": "primary", "color": "#00B900",
                          "action": {"type": "message", "label": "✅ 確認送出", "text": "確認送出加班申請"}},
                         {"type": "button", "style": "primary", "color": "#FF3B30",
                          "action": {"type": "message", "label": "❌ 取消", "text": "取消加班申請"}}
                     ]}
                ]
            }
        }

        line_bot_api.reply_message(
            event.reply_token,
            FlexSendMessage(alt_text="請確認加班申請", contents=flex_message)
        )
        return True

    # Step 3: 確認送出
    if step == 3:
        if text == "確認送出加班申請":
            try:
                save_overtime_to_sheet(user_id, session["date"], session["time"], session["reason"])
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="✅ 加班申請已送出"))
            except Exception as e:
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"❌ 送出失敗：{e}"))
            clear_session(user_id)
            return True

        if text == "取消加班申請":
            clear_session(user_id)
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="已取消加班申請"))
            return True

    return False
