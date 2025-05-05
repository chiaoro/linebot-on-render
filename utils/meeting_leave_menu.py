from linebot.models import FlexSendMessage

def get_meeting_leave_menu():
    return FlexSendMessage(
        alt_text="院務會議請假",
        contents={
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "spacing": "md",
                "contents": [
                    {
                        "type": "text",
                        "text": "📋 院務會議請假",
                        "weight": "bold",
                        "size": "lg"
                    },
                    {
                        "type": "text",
                        "text": "請問您是否出席院務會議？",
                        "wrap": True
                    }
                ]
            },
            "footer": {
                "type": "box",
                "layout": "horizontal",
                "spacing": "md",
                "contents": [
                    {
                        "type": "button",
                        "style": "primary",
                        "color": "#00C851",
                        "action": {
                            "type": "message",
                            "label": "✅ 出席",
                            "text": "我要出席院務會議"
                        }
                    },
                    {
                        "type": "button",
                        "style": "primary",
                        "color": "#ff4444",
                        "action": {
                            "type": "message",
                            "label": "❌ 請假",
                            "text": "我要請假院務會議"
                        }
                    }
                ]
            }
        }
    )
