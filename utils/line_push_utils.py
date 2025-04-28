import os
from dotenv import load_dotenv
from linebot import LineBotApi
from linebot.models import TextSendMessage

# ✅ 載入環境變數
load_dotenv()

# ✅ 初始化 LINE Bot API
line_bot_api = LineBotApi(os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))

# ✅ 這是簡單版推播函式（支援個人推播）
def push_text_to_user(user_id, text):
    try:
        line_bot_api.push_message(user_id, TextSendMessage(text=text))
    except Exception as e:
        print(f"❌ 推播失敗：{e}")
