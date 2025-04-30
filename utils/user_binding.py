from linebot.models import TextSendMessage, FlexSendMessage
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
# 綁定流程步驟：顯示開始綁定的 Flex Bubble
def send_bind_start_flex(line_bot_api, reply_token):
    bubble = {
        "type": "bubble",
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "contents": [
                {"type": "text", "text": "🔒 綁定身份", "weight": "bold", "size": "xl"},
                {"type": "text", "text": "歡迎您！請點選下方按鈕開始綁定，以利系統識別您的身分。", "size": "sm", "wrap": True}
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
    line_bot_api.reply_message(reply_token, flex)

# 步驟二：要求輸入姓名
def ask_for_name(line_bot_api, reply_token):
    line_bot_api.reply_message(reply_token, TextSendMessage(text="👤 請輸入您的姓名，以完成身分綁定。"))

# 步驟三：確認綁定完成
def confirm_binding(line_bot_api, reply_token, name, user_id):
    bubble = {
        "type": "bubble",
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "contents": [
                {"type": "text", "text": "✅ 綁定完成", "weight": "bold", "size": "xl", "color": "#1DB446"},
                {"type": "text", "text": f"歡迎 {name}  ，您好！", "wrap": True, "size": "sm"},
                {"type": "text", "text": f"您的個人 ID：{user_id}", "wrap": True, "size": "sm", "color": "#666666"}
            ]
        }
    }
    flex = FlexSendMessage(alt_text="綁定完成", contents=bubble)
    line_bot_api.reply_message(reply_token, flex)
