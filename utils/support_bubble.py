# utils/support_bubble.py

def get_support_adjustment_bubble(doctor_name, department, original, method, reason):
    return {
        "type": "bubble",
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "contents": [
                {"type": "text", "text": "✅ 支援醫師調診單", "weight": "bold", "size": "lg"},
                {"type": "text", "text": f"👨‍⚕️ 醫師：{doctor_name}"},
                {"type": "text", "text": f"🏥 科別：{department}"},
                {"type": "text", "text": f"📅 原門診：{original}"},
                {"type": "text", "text": f"🔁 處理方式：{method}"},
                {"type": "text", "text": f"📝 原因：{reason}"}
            ]
        }
    }
