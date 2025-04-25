# utils/line_push_utils.py

import os
from dotenv import load_dotenv
from linebot import LineBotApi
from linebot.models import TextSendMessage

load_dotenv()
line_bot_api = LineBotApi(os.environ['LINE_CHANNEL_ACCESS_TOKEN'])

def push_to_doctor(user_id, msg):
    try:
        line_bot_api.push_message(user_id, TextSendMessage(text=msg))
        print(f"✅ 已推播訊息給 {user_id}：{msg}")
    except Exception as e:
        print(f"❌ 推播失敗：{e}")
