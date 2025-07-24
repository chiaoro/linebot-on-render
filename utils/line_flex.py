def build_doctor_flex(data):
    return {
        "type": "bubble",
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {"type": "text", "text": f"醫師：{data['姓名']}", "weight": "bold", "size": "lg"},
                {"type": "text", "text": f"出生：{data['出生年月']}", "size": "sm"},
                {"type": "text", "text": f"性別：{data['性別']}  年齡：{data['年齡']}", "size": "sm"},
                {"type": "text", "text": f"公務機：{data['公務機']}", "size": "sm"},
                {"type": "text", "text": f"私人手機：{data['私人手機']}", "size": "sm"},
                {"type": "text", "text": f"地址：{data['地址']}", "wrap": True, "size": "sm"},
                {"type": "text", "text": f"在澎地址：{data['在澎地址']}", "wrap": True, "size": "sm"},
                {"type": "text", "text": f"Email：{data['email']}", "size": "sm"},
                {"type": "text", "text": f"緊急聯絡人：{data['緊急聯絡人']}", "wrap": True, "size": "sm"}
            ]
        }
    }