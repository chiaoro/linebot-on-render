# utils/flex_templates.py

def get_adjustment_result_bubble(original, method, reason):
    return {
        "type": "bubble",
        "header": {
            "type": "box",
            "layout": "vertical",
            "contents": [{
                "type": "text",
                "text": "✅ 調整單已送出",
                "weight": "bold",
                "color": "#1DB446",
                "size": "lg"
            }]
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "contents": [
                {"type": "text", "text": f"原門診：{original}", "wrap": True},
                {"type": "text", "text": f"處理方式：{method}", "wrap": True},
                {"type": "text", "text": f"原因：{reason}", "wrap": True}
            ]
        },
        "footer": {
            "type": "box",
            "layout": "horizontal",
            "contents": [{
                "type": "text",
                "text": "如有誤請洽醫療部秘書",
                "size": "sm",
                "color": "#aaaaaa"
            }]
        }
    }
