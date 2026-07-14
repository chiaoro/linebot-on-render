# utils/user_binding.py

from linebot.models import TextSendMessage, FlexSendMessage
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json, os

# ✅ 暫存每位使用者綁定狀態（例如：等待輸入姓名）
user_states = {}

# ✅ Google Sheets 連線
def get_worksheet():
    SCOPE = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds_dict = json.loads(os.environ.get("GOOGLE_CREDENTIALS"))
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
    gc = gspread.authorize(creds)
    sheet = gc.open_by_url("https://docs.google.com/spreadsheets/d/1fHf5XlbvLMd6ytAh_t8Bsi5ghToiQHZy1NlVfEG7VIo/edit")
    return sheet.worksheet("UserMapping")  # 確認你的分頁名稱

# ✅ 確保使用者 ID 存在
def ensure_user_id_exists(user_id):
    worksheet = get_worksheet()
    existing_ids = worksheet.col_values(1)
    if user_id not in existing_ids:
        worksheet.append_row([user_id, "", ""])  # 留空姓名與科別
        print(f"📌 新增未綁定 userId：{user_id}")

# ✅ 綁定 Step 1：顯示綁定開始 Flex
def send_bind_start_flex(line_bot_api, reply_token):
    bubble = {
        "type": "bubble",
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "contents": [
                {"type": "text", "text": "🔒 綁定身份", "weight": "bold", "size": "xl"},
                {"type": "text", "text": "請點選下方按鈕開始綁定，以利系統識別您的身分。", "size": "sm", "wrap": True}
            ]
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "button",
                    "action": {"type": "message", "label": "我要綁定", "text": "我要綁定"},
                    "style": "primary",
                    "color": "#1DB446"
                }
            ]
        }
    }
    flex = FlexSendMessage(alt_text="綁定身份", contents=bubble)
    return flex

# ✅ 綁定 Step 2：請輸入姓名
def ask_for_name():
    return TextSendMessage(text="👤 請輸入您的姓名，以完成身分綁定。")

# ✅ 綁定 Step 3：完成綁定並回覆 Flex
def confirm_binding(user_id, name):
    bubble = {
        "type": "bubble",
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "contents": [
                {"type": "text", "text": "✅ 綁定完成", "weight": "bold", "size": "xl", "color": "#1DB446"},
                {"type": "text", "text": f"歡迎 {name} ，您好！", "wrap": True, "size": "sm"},
                {"type": "text", "text": f"您的個人 ID：{user_id}", "wrap": True, "size": "sm", "color": "#666666"}
            ]
        }
    }
    flex = FlexSendMessage(alt_text="綁定完成", contents=bubble)
    return flex

# ✅ 整合式主處理：handle_user_binding（你只要在 app.py 呼叫這個就好）
def handle_user_binding(event, line_bot_api):
    user_id = event.source.user_id
    msg = event.message.text.strip()

    # 使用者點擊「我要綁定」
    if msg == "我要綁定":
        ensure_user_id_exists(user_id)
        user_states[user_id] = "awaiting_name"
        return ask_for_name()

    # 使用者正在輸入姓名
    if user_id in user_states and user_states[user_id] == "awaiting_name":
        name = msg
        worksheet = get_worksheet()
        try:
            cell = worksheet.find(user_id)
            if cell:
                worksheet.update_cell(cell.row, 2, name)  # 第二欄為姓名
        except:
            print("❌ 找不到 userId")
        del user_states[user_id]
        return confirm_binding(user_id, name)

    return None  # 非綁定相關訊息，交由主程式處理
