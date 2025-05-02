# utils/line_utils.py

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
