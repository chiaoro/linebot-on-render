from linebot.models import TextSendMessage
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json, os

# ✅暫存狀態
user_states = {}

# ✅初始化 Google Sheets 連線
def get_worksheet():
    SCOPE = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds_dict = json.loads(os.environ.get("GOOGLE_CREDENTIALS"))
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
    gc = gspread.authorize(creds)
    sheet = gc.open_by_url("https://docs.google.com/spreadsheets/d/1fHf5XlbvLMd6ytAh_t8Bsi5ghToiQHZy1NlVfEG7VIo/edit")
    return sheet.worksheet("UserMapping")  # 請確認分頁名稱為此



# ✅自動補 userId（如果未綁定）
def ensure_user_id_exists(user_id):
    worksheet = get_worksheet()
    existing_ids = worksheet.col_values(1)
    if user_id not in existing_ids:
        worksheet.append_row([user_id, "", ""])  # 留空姓名與科別供你後補
        print(f"📌 新增未綁定 userId：{user_id}")





# ✅主處理流程
def handle_user_binding(event, line_bot_api):
    user_id = event.source.user_id
    msg = event.message.text.strip()

    # 第一步：觸發綁定
    if msg == "我要綁定":
        user_states[user_id] = {"step": 1}
        return TextSendMessage(text="請輸入您的姓名以完成綁定")

    # 第二步：儲存使用者對照資料
    if user_id in user_states and user_states[user_id].get("step") == 1:
        doctor_name = msg
        worksheet = get_worksheet()

        # 檢查是否已存在相同 user_id（避免重複）
        existing_ids = worksheet.col_values(1)
        if user_id in existing_ids:
            return TextSendMessage(text="⚠️ 您已完成綁定，無需重複操作")

        # 寫入資料：LINE_USER_ID｜姓名｜（空白，等你手動填入科別）
        worksheet.append_row([user_id, doctor_name, ""])
        user_states.pop(user_id)
        return TextSendMessage(text=f"✅ 綁定完成，您好「{doctor_name}」！")

    return None  # 非綁定流程，不處理
