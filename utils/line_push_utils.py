# utils/line_push_utils.py

import os
from dotenv import load_dotenv
from linebot import LineBotApi
from linebot.models import TextSendMessage

load_dotenv()

# 初始化 LINE Bot
line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))

def push_to_doctor(user_id, text):
    """推送訊息到特定醫師（或使用者）"""
    try:
        line_bot_api.push_message(user_id, TextSendMessage(text=text))
    except Exception as e:
        print(f"❌ 推播失敗：{e}")
