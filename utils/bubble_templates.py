from linebot.models import FlexSendMessage

def main_menu_bubble():
    return FlexSendMessage(
        alt_text="主選單",
        contents={
            "type": "bubble",
            "hero": {
                "type": "image",
                "url": "https://i.imgur.com/HlZsJ9k.png",  # 可改為你想放的 banner
                "size": "full",
                "aspectRatio": "20:13",
                "aspectMode": "cover"
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "spacing": "sm",
                "contents": [
                    { "type": "text", "text": "🔧 主選單", "weight": "bold", "size": "xl" },
                    { "type": "text", "text": "請選擇您需要的服務", "wrap": True }
                ]
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "spacing": "sm",
                "contents": [
                    {
                        "type": "button",
                        "style": "primary",
                        "action": { "type": "message", "label": "我要申請夜點費", "text": "我要夜點費" }
                    },
                    {
                        "type": "button",
                        "style": "primary",
                        "action": { "type": "message", "label": "我要調整門診", "text": "我要調診" }
                    },
                    {
                        "type": "button",
                        "style": "primary",
                        "action": { "type": "message", "label": "我要請假", "text": "我要請假" }
                    },
                    {
                        "type": "button",
                        "style": "secondary",
                        "action": { "type": "message", "label": "🔄 再看一次主選單", "text": "主選單" }
                    }
                ]
            }
        }
    )
