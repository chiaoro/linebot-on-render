# utils/line_push_utils.py
import os
from linebot import LineBotApi
from linebot.models import TextSendMessage

LINE_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
line_bot_api = LineBotApi(LINE_TOKEN)

def push_text_to_user(reply_token: str, text: str):
    line_bot_api.reply_message(reply_token, TextSendMessage(text=text))


def push_text_to_group(group_id: str, text: str):
    line_bot_api.push_message(group_id, TextSendMessage(text=text))
