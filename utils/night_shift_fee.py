# utils/night_shift_fee.py

import os
from datetime import datetime, date
from linebot.models import TextSendMessage
from utils.gspread_client import get_gspread_client
from utils.line_push_utils import push_text_to_user, push_text_to_group
from linebot.models import FlexSendMessage




# 表單與分頁設定
SHEET_URL = "https://docs.google.com/spreadsheets/d/1XpX1l7Uf93XWNEYdZsHx-3IXpPf4Sb9Zl0ARGa4Iy5c/edit"
WORKSHEET_NAME = "夜點費申請紀錄"
GROUP_ID = os.getenv("All_doctor_group_id")

def handle_night_shift_request(user_id, user_msg):
    gc = get_gspread_client()
    sheet = gc.open_by_url(SHEET_URL).worksheet(WORKSHEET_NAME)
    """
    處理醫師送出的夜點費申請資料（文字）
    """
    try:
        sheet = gc.open_by_url(SHEET_URL).worksheet(WORKSHEET_NAME)
        user_text = user_msg.replace("夜點費申請", "").strip()
        now = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
        sheet.append_row([now, user_text, "未提醒"])
        push_text_to_user(user_id, f"✅ 已收到您的申請：{user_text}\n我們將於每月 1~5 號進行催繳提醒。")
    except Exception as e:
        print(f"❌ handle_night_shift_request 發生錯誤：{e}")
        push_text_to_user(user_id, "⚠️ 系統異常，請稍後再試或聯絡秘書")

def daily_night_fee_reminder():
    """
    每月 1~5 號提醒尚未繳交上月夜點費的醫師（避免重複提醒）
    """
    try:
        today = date.today()
        if not (1 <= today.day <= 5):
            return

        sheet = gc.open_by_url(SHEET_URL).worksheet(WORKSHEET_NAME)
        records = sheet.get_all_records()
        headers = sheet.row_values(1)

        for idx, rec in enumerate(records, start=2):  # 從第2列開始（第1列是標題）
            try:
                apply_time = rec.get("時間", "")
                doctor = rec.get("醫師姓名")
                status = rec.get("提醒狀態", "")

                apply_date = datetime.strptime(apply_time, "%Y/%m/%d %H:%M:%S").date()
                last_month = today.month - 1 if today.month > 1 else 12

                if apply_date.month == last_month and status != "已提醒":
                    text = f"📌 {doctor}，請於本月 1~5 號繳交 {apply_date.strftime('%Y/%m')} 夜點費資料，謝謝！"
                    push_text_to_group(GROUP_ID, text)

                    # 更新狀態為已提醒
                    status_col = headers.index("提醒狀態") + 1
                    sheet.update_cell(idx, status_col, "已提醒")

            except Exception as inner_e:
                print(f"⚠️ 單筆提醒處理錯誤（第 {idx} 行）：{inner_e}")
                continue

    except Exception as e:
        print(f"❌ daily_night_fee_reminder 發生錯誤：{e}")

def run_night_shift_reminder():
    """
    提供給 /night-shift-reminder 路由觸發的入口函式
    """
    print("📡 執行夜點費提醒...")
    daily_night_fee_reminder()





def get_night_fee_success(dates: str, count: int) -> FlexSendMessage:
    return FlexSendMessage(
        alt_text="✅ 夜點費資料已送出",
        contents={
            "type": "bubble",
            "size": "kilo",
            "body": {
                "type": "box",
                "layout": "vertical",
                "spacing": "md",
                "contents": [
                    {
                        "type": "text",
                        "text": "✅ 夜點費資料已送出",
                        "weight": "bold",
                        "size": "lg",
                        "color": "#00C851"
                    },
                    {
                        "type": "text",
                        "text": f"📆 日期：{dates}（共 {count} 班）",
                        "wrap": True,
                        "color": "#555555"
                    }
                ]
            }
        }
    )
