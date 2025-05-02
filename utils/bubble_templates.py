from linebot.models import FlexSendMessage

def main_menu_v2_bubble():
    return FlexSendMessage(
        alt_text="主選單",
        contents={
            "type": "bubble",
            "size": "mega",
            "body": {
                "type": "box",
                "layout": "vertical",
                "spacing": "md",
                "contents": [
                    {
                        "type": "text",
                        "text": "📋 請選擇服務類別",
                        "weight": "bold",
                        "size": "xl",
                        "color": "#222222"
                    }
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
                        "action": { "type": "message", "label": "門診調整服務", "text": "門診調整服務" }
                    },
                    {
                        "type": "button",
                        "style": "primary",
                        "action": { "type": "message", "label": "值班調整服務", "text": "值班調整服務" }
                    },
                    {
                        "type": "button",
                        "style": "primary",
                        "action": { "type": "message", "label": "支援醫師服務", "text": "支援醫師服務" }
                    },
                    {
                        "type": "button",
                        "style": "primary",
                        "action": { "type": "message", "label": "新進醫師服務", "text": "新進醫師服務" }
                    },
                    {
                        "type": "button",
                        "style": "primary",
                        "action": { "type": "message", "label": "其他表單服務", "text": "其他表單服務" }
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
