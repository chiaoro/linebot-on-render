# handlers/night_fee_handler.py
from linebot.models import TextSendMessage

def handle_night_fee(event, user_id, text, line_bot_api):
    if text == "夜點費申請":
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請輸入日期…"))
        return True
    return False
