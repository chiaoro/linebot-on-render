from linebot.models import TextSendMessage
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json, os

# 使用者暫存狀態
user_states = {}

# 初始化 Google Sheets
def get_worksheet():
    SCOPE = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds_dict = json.loads(os.environ.get("GOOGLE_CREDENTIALS"))
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
    gc = gspread.authorize(creds)
    sheet = gc.open_by_url(os.environ.get("USER_MAPPING_SHEET_URL"))  # 你放在 .env 中
    return sheet.worksheet("使用者對照表")

# 處理綁定邏輯
def handle_user_binding(event, line_bot_api):
    user_id = event.source.user_id
    msg = event.message.text.strip()

    if msg == "我要綁定":
        user_states[user_id] = {"step": 1}
        return TextSendMessage(text="請輸入您的姓名以完成綁定")

    if user_id in user_states and user_states[user_id].get("step") == 1:
        doctor_name = msg
        worksheet = get_worksheet()
        worksheet.append_row([user_id, doctor_name])
        user_states.pop(user_id)
        return TextSendMessage(text=f"✅ 已成功綁定「{doctor_name}」，未來可進行推播")

    return None  # 非綁定流程，不處理
