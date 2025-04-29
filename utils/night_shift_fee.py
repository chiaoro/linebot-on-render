# utils/night_shift_fee.py
import os, json
from datetime import datetime, date
from linebot.models import TextSendMessage
import gspread
from utils.gspread_client import gc
from oauth2client.service_account import ServiceAccountCredentials
from utils.line_push_utils import push_text_to_user, push_text_to_group

# ✅ 改成等到用到時才去開 Sheet
def get_night_shift_sheet():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds_dict = json.loads(os.getenv("GOOGLE_CREDENTIALS"))
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    gc = gspread.authorize(creds)
    
    sheet_url = "https://docs.google.com/spreadsheets/d/1XpX1l7Uf93XWNEYdZsHx-3IXpPf4Sb9Zl0ARGa4Iy5c/edit"
    worksheet_name = "夜點費申請紀錄"  # 這個如果不存在，會報錯！
    
    sheet = gc.open_by_url(SHEET_URL).worksheet(WORKSHEET_NAME)
    return sheet



def handle_night_shift_request(user_id, user_msg):
    SCOPE = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds_dict = json.loads(os.getenv("GOOGLE_CREDENTIALS"))
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
    gc = gspread.authorize(creds)

    sheet = gc.open_by_url(SHEET_URL).worksheet(WORKSHEET_NAME)
    user_text = event.message.text.replace("夜點費", "").strip()
    now = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
    # 假設試算表欄位為 [時間, 醫師姓名, 提醒狀態]
    sheet.append_row([now, user_text, "未提醒"])
    push_text_to_user(event.reply_token, f"已收到您的申請：{user_text}，我們將於每月 1~5 號進行催繳提醒。")


def daily_night_fee_reminder():
    """每月 1~5 號，提醒尚未繳交上月夜點費者"""
    today = date.today()
    if not (1 <= today.day <= 5):
        return
    sheet = GC.open_by_url(SHEET_URL).worksheet(WORKSHEET_NAME)
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
