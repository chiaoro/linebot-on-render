# utils/adjust_bubble.py

def get_adjustment_bubble(original, method, reason):
    return {
        "type": "bubble",
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "contents": [
                {"type": "text", "text": "✅ 門診調整通知", "weight": "bold", "size": "lg"},
                {"type": "text", "text": f"📅 原門診：{original}"},
                {"type": "text", "text": f"🔁 處理方式：{method}"},
                {"type": "text", "text": f"📝 原因：{reason}"}
            ]
        }
    }
