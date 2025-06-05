# handlers/stats_handler.py

import re
from linebot.models import TextSendMessage

# ✅ 統計記錄資料結構
attendance_data = {
    "active": False,
    "records": {}  # user_id: {"name": 使用者名稱, "count": 整數}
}

def handle_stats(event, user_id, text, line_bot_api, user_name="未知使用者"):
    text = text.strip()
    reply_token = event.reply_token

    # ✅ 開啟統計
    if text == "開啟統計":
        attendance_data["active"] = True
        attendance_data["records"] = {}
        line_bot_api.reply_message(
            reply_token,
            TextSendMessage("🟢 統計功能已開啟！請大家踴躍 +1（如需取消請 -1）")
        )
        return True

    # ✅ 結束統計
    if text == "結束統計":
        if not attendance_data["active"]:
            line_bot_api.reply_message(reply_token, TextSendMessage("⚠️ 尚未開啟統計功能"))
            return True

        summary_lines = []
        total = 0
        for record in attendance_data["records"].values():
            if record["count"] != 0:
                summary_lines.append(f"{record['name']}: {record['count']}")
                total += record["count"]

        summary = "\n".join(summary_lines) if summary_lines else "（尚無回覆）"
        result_text = f"🔴 統計已結束：\n{summary}\n\n👥 總人數為：{total}人 🙌"

        line_bot_api.reply_message(reply_token, TextSendMessage(result_text))

        # 若你不想清除記錄，也可以註解掉這行
        attendance_data["active"] = False
        return True

    # ✅ +1 / -1 類統計
    if attendance_data["active"]:
        match = re.match(r"^([+-])(\d+)$", text)
        if match:
            sign, number = match.groups()
            count = int(number)
            if sign == "-":
                count *= -1

            if user_id not in attendance_data["records"]:
                attendance_data["records"][user_id] = {"name": user_name, "count": 0}

            attendance_data["records"][user_id]["count"] += count
            return True

    return False
