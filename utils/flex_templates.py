# utils/flex_templates.py

def get_adjustment_bubble(original, method, reason):
    """調診／代診結果 Flex Bubble"""
    return {
        "type": "bubble",
        "header": {
            "type": "box",
            "layout": "vertical",
            "contents": [{
                "type": "text",
                "text": "✅ 門診調整已送出",
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
                {"type": "text", "text": f"📅 原門診：{original}", "wrap": True},
                {"type": "text", "text": f"🛠️ 處理方式：{method}", "wrap": True},
                {"type": "text", "text": f"📝 調整原因：{reason}", "wrap": True}
            ]
        },
        "footer": {
            "type": "box",
            "layout": "horizontal",
            "contents": [{
                "type": "text",
                "text": "如有誤請洽巧柔",
                "size": "sm",
                "color": "#aaaaaa"
            }]
        }
    }


def get_duty_swap_bubble(shift_type, original_doctor, original_date, target_doctor, swap_date, reason):
    """值班調換結果 Flex Bubble"""
    return {
        "type": "bubble",
        "header": {
            "type": "box",
            "layout": "vertical",
            "contents": [{
                "type": "text",
                "text": "✅ 值班調換已送出",
                "weight": "bold",
                "color": "#007AFF",
                "size": "lg"
            }]
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "contents": [
                {"type": "text", "text": f"🧑‍⚕️ 原值班醫師：{original_doctor}", "wrap": True},
                {"type": "text", "text": f"📅 原值班日：{original_date}", "wrap": True},
                {"type": "text", "text": f"🔁 班別：{shift_type}", "wrap": True},
                {"type": "text", "text": f"🤝 對調醫師：{target_doctor}", "wrap": True},
                {"type": "text", "text": f"📅 調換至：{swap_date}", "wrap": True},
                {"type": "text", "text": f"📝 原因：{reason}", "wrap": True}
            ]
        },
        "footer": {
            "type": "box",
            "layout": "horizontal",
            "contents": [{
                "type": "text",
                "text": "如有誤請洽巧柔",
                "size": "sm",
                "color": "#aaaaaa"
            }]
        }
    }


def get_duty_proxy_bubble(shift_type, original_doctor, original_date, proxy_doctor, reason):
    return {
        "type": "bubble",
        "header": {
            "type": "box",
            "layout": "vertical",
            "contents": [{
                "type": "text",
                "text": "✅ 值班代理已送出",
                "weight": "bold",
                "color": "#FFA500",
                "size": "lg"
            }]
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "contents": [
                {"type": "text", "text": f"🧑‍⚕️ 醫師：{original_doctor}", "wrap": True},
                {"type": "text", "text": f"📅 原值班：{shift_type} {original_date}", "wrap": True},
                {"type": "text", "text": f"🙋‍♂️ 代理醫師：{proxy_doctor}", "wrap": True},
                {"type": "text", "text": f"📝 原因：{reason}", "wrap": True}
            ]
        },
        "footer": {
            "type": "box",
            "layout": "horizontal",
            "contents": [{
                "type": "text",
                "text": "如有誤請洽巧柔",
                "size": "sm",
                "color": "#aaaaaa"
            }]
        }
    }

def get_duty_swap_bubble(shift_type, original_doctor, original_date, target_doctor, swap_date, reason):
    return {
        "type": "bubble",
        "header": {
            "type": "box",
            "layout": "vertical",
            "contents": [{
                "type": "text",
                "text": "✅ 值班調換已送出",
                "weight": "bold",
                "color": "#007AFF",
                "size": "lg"
            }]
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "contents": [
                {"type": "text", "text": f"🧑‍⚕️ 醫師：{original_doctor}", "wrap": True},
                {"type": "text", "text": f"📅 原值班：{shift_type} {original_date}", "wrap": True},
                {"type": "text", "text": f"🤝 對調醫師：{target_doctor}", "wrap": True},
                {"type": "text", "text": f"📅 調換至：{swap_date}", "wrap": True},
                {"type": "text", "text": f"📝 原因：{reason}", "wrap": True}
            ]
        },
        "footer": {
            "type": "box",
            "layout": "horizontal",
            "contents": [{
                "type": "text",
                "text": "如有誤請洽巧柔",
                "size": "sm",
                "color": "#aaaaaa"
            }]
        }
    }



def get_support_adjustment_bubble(doctor_name, original, method, reason):
    return {
        "type": "bubble",
        "header": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {"type": "text", "text": "✅ 支援醫師調診申請已送出", "weight": "bold", "size": "lg", "color": "#00A37A"}
            ]
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "contents": [
                {"type": "text", "text": f"👨‍⚕️ 醫師：{doctor_name}", "wrap": True},
                {"type": "text", "text": f"📅 原門診：{original}", "wrap": True},
                {"type": "text", "text": f"📋 處理方式：{method}", "wrap": True},
                {"type": "text", "text": f"📝 原因：{reason}", "wrap": True}
            ]
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": "📌 若需修改請洽巧柔",
                    "size": "sm",
                    "color": "#888888"
                }
            ]
        }
    }
