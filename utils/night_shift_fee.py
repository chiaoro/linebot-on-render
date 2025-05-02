#utils/night_shift_fee.py

import os, json
from datetime import datetime, date
from linebot.models import TextSendMessage
import gspread
from utils.gspread_client import gc
from utils.line_push_utils import push_text_to_user, push_text_to_group
from oauth2client.service_account import ServiceAccountCredentials

SHEET_URL = "https://docs.google.com/spreadsheets/d/1XpX1l7Uf93XWNEYdZsHx-3IXpPf4Sb9Zl0ARGa4Iy5c/edit"
WORKSHEET_NAME = "夜點費申請紀錄"
GROUP_ID = os.getenv("All_doctor_group_id")  # 推播群組ID

def handle_night_shift_request(user_id, user_msg):
    sheet = gc.open_by_url(SHEET_URL).worksheet(WORKSHEET_NAME)
    user_text = user_msg.replace("夜點費申請", "").strip()
    now = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
    # 假設試算表欄位為 [時間, 醫師姓名, 提醒狀態]
    sheet.append_row([now, user_text, "未提醒"])
    push_text_to_user(user_id, f"✅ 已收到您的申請：{user_text}\n我們將於每月 1~5 號進行催繳提醒。")

def daily_night_fee_reminder():
    """每月 1~5 號，提醒尚未繳交上月夜點費者"""
    today = date.today()
    if not (1 <= today.day <= 5):
        return
    sheet = gc.open_by_url(SHEET_URL).worksheet(WORKSHEET_NAME)
    records = sheet.get_all_records()
    for idx, rec in enumerate(records, start=2):
        apply_time = rec.get("時間", "")
        doctor = rec.get("醫師姓名")
        status = rec.get("提醒狀態")
        # 檢查是否為上個月且未提醒
        try:
            apply_date = datetime.strptime(apply_time, "%Y/%m/%d %H:%M:%S").date()
        except:
            continue
        last_month = today.month - 1 or 12
        if apply_date.month == last_month and status != "已提醒":
            text = f"📌 {doctor}，請於本月 1~5 號繳交 {apply_date.strftime('%Y/%m')} 夜點費資料，謝謝！"
            push_text_to_group(GROUP_ID, text)
            sheet.update_cell(idx, list(records[0].keys()).index("提醒狀態")+1, "已提醒")


def run_night_shift_reminder():
    """提供給 /night-shift-reminder route 使用"""
    daily_night_fee_reminder()
