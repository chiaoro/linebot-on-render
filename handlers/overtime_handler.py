from linebot.models import TextSendMessage, FlexSendMessage
from utils.session_manager import get_session, set_session, clear_session
from utils.google_sheets import get_doctor_info  # ✅ 引入工具
import os
import json
from googleapiclient.discovery import build
from google.oauth2 import service_account
from datetime import datetime
import requests

# ✅ Google Sheet 設定
OVERTIME_SHEET_ID = "1pb5calRrKlCWx16XENcit85pF0qLoH1lvMfGI_WZ_n8"  # 加班申請表
USER_MAPPING_SHEET_URL = "https://docs.google.com/spreadsheets/d/1fHf5XlbvLMd6ytAh_t8Bsi5ghToiQHZy1NlVfEG7VIo/edit"  # 使用者對照表

# ✅ 主流程
def handle_overtime(event, user_id, text, line_bot_api):
    session = get_session(user_id)

    # ✅ 啟動流程
    if text == "加班申請":
        set_session(user_id, {"step": 0, "type": "overtime"})
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請輸入加班日期（格式：YYYY-MM-DD）"))
        return True

    # ✅ 判斷是否在加班流程
    if session.get("type") != "overtime":
        return False

    step = session.get("step", 0)

    # Step 0：日期
    if step == 0:
        session["date"] = text
        session["step"] = 1
        set_session(user_id, session)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請輸入加班時間（格式：HH:MM-HH:MM）"))
        return True

    # Step 1：時間
    if step == 1:
        session["time"] = text
        session["step"] = 2
        set_session(user_id, session)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請輸入加班事由"))
        return True

    # Step 2：事由 → 顯示確認畫面
    if step == 2:
        session["reason"] = text

        # ✅ 從 Google Sheet 取得醫師資訊
        doctor_info = get_doctor_info(USER_MAPPING_SHEET_URL, user_id)
        doctor_name = doctor_info.get("姓名", "未知醫師")
        doctor_dept = doctor_info.get("科別", "未填科別")

        confirm_flex = {
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {"type": "text", "text": "📋 請確認加班申請", "weight": "bold", "size": "lg"},
                    {"type": "text", "text": f"科別：{doctor_dept}"},
                    {"type": "text", "text": f"姓名：{doctor_name}"},
                    {"type": "text", "text": f"日期：{session['date']}"},
                    {"type": "text", "text": f"時間：{session['time']}"},
                    {"type": "text", "text": f"事由：{session['reason']}"}
                ]
            },
            "footer": {
                "type": "box",
                "layout": "horizontal",
                "contents": [
                    {
                        "type": "button",
                        "style": "primary",
                        "color": "#00B900",
                        "action": {"type": "message", "label": "✅ 確認送出", "text": "確認送出加班申請"}
                    },
                    {
                        "type": "button",
                        "style": "primary",
                        "color": "#FF0000",
                        "action": {"type": "message", "label": "❌ 取消", "text": "取消加班申請"}
                    }
                ]
            }
        }

        session["doctor_name"] = doctor_name
        session["doctor_dept"] = doctor_dept
        session["step"] = 3
        set_session(user_id, session)

        line_bot_api.reply_message(event.reply_token, FlexSendMessage(alt_text="請確認加班申請", contents=confirm_flex))
        return True

    # Step 3：確認送出
    if step == 3:
        if text == "確認送出加班申請":
            try:
                info = json.loads(os.getenv("GOOGLE_CREDENTIALS"))
                creds = service_account.Credentials.from_service_account_info(
                    info, scopes=['https://www.googleapis.com/auth/spreadsheets']
                )
                service = build('sheets', 'v4', credentials=creds)
                sheet = service.spreadsheets()

                sheet.values().append(
                    spreadsheetId=OVERTIME_SHEET_ID,
                    range="加班申請!A:F",
                    valueInputOption="RAW",
                    body={
                        "values": [[
                            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),  # 時間戳記
                            session["doctor_dept"],  # 醫師科別
                            session["doctor_name"],  # 醫師姓名
                            session["date"],         # 加班日期
                            session["time"],         # 加班時間
                            session["reason"]        # 事由
                        ]]
                    }
                ).execute()

                clear_session(user_id)
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="✅ 加班申請已送出！"))
            except Exception as e:
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"❌ 送出失敗：{str(e)}"))
            return True

        if text == "取消加班申請":
            clear_session(user_id)
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="❌ 加班申請已取消"))
            return True

    return False
