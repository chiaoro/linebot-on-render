import os
from dotenv import load_dotenv
from linebot import LineBotApi
from linebot.models import TextSendMessage

load_dotenv()

line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))

def push_text_to_user(user_id, text):
    """推播訊息給單一使用者"""
    try:
        line_bot_api.push_message(user_id, TextSendMessage(text=text))
    except Exception as e:
        print(f"❌ 推播給使用者失敗：{e}")

def push_text_to_group(group_id, text):
    """推播訊息到群組"""
    try:
        line_bot_api.push_message(group_id, TextSendMessage(text=text))
    except Exception as e:
        print(f"❌ 推播到群組失敗：{e}")
