# utils/line_utils.py
import re
from utils.google_sheets import get_doctor_name
from linebot.models import TextMessage, PostbackEvent

def get_event_text(event):
    """
    統一取得使用者輸入的文字內容，支援文字訊息與 postback。
    回傳已 strip() 去除空白的字串。
    """
    if isinstance(event, PostbackEvent):
        return event.postback.data.strip()
    elif hasattr(event, "message") and isinstance(event.message, TextMessage):
        return event.message.text.strip()
    return ""

def is_trigger(event, keywords):
    """
    判斷這次 event 是否是某個關鍵字觸發（文字或 postback）。
    使用範例：
        if is_trigger(event, ["我要調診", "我要休診"]):
            ...
    """
    text = get_event_text(event)
    return text in keywords



def get_event_text(event):
    if isinstance(event, PostbackEvent):
        return event.postback.data.strip()
    elif hasattr(event, "message") and isinstance(event.message, TextMessage):
        return event.message.text.strip()
    return ""



def is_stat_trigger(text):
    return re.match(r"^(開啟統計|結束統計|[+-]\d+)$", text.strip()) is not None



def get_safe_user_name(event):
    try:
        if event.source.type == "user":
            from linebot import LineBotApi
            import os
            line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
            profile = line_bot_api.get_profile(event.source.user_id)
            return profile.display_name
        else:
            return get_doctor_name(event.source.user_id)
    except Exception as e:
        print(f"⚠️ 無法取得使用者名稱：{e}")
        return "未知使用者"
