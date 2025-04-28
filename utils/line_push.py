# utils/line_push.py

import os
from dotenv import load_dotenv
from linebot import LineBotApi
from linebot.models import TextSendMessage

load_dotenv()

line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))

def push_text_to_user(user_id, text):
    line_bot_api.push_message(user_id, TextSendMessage(text=text))

def push_text_to_group(group_id, text):
    line_bot_api.push_message(group_id, TextSendMessage(text=text))
