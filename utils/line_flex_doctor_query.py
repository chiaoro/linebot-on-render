# utils/line_flex_doctor_query.py
def build_doctor_flex(info):
    return {
        "type": "bubble",
        "size": "mega",
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {"type": "text", "text": f"👨‍⚕️ {info['姓名']}", "weight": "bold", "size": "xl"},
                {"type": "text", "text": f"科別：{info['科別']}"},
                {"type": "text", "text": f"職稱：{info['職稱']}"},
                {"type": "text", "text": f"手機：{info['手機']}"},
                {"type": "text", "text": f"地址：{info['地址']}"},
                {"type": "text", "text": f"在澎地址：{info['在澎地址']}"},
                {"type": "text", "text": f"Email：{info['Email']}"}
            ]
        }
    }
