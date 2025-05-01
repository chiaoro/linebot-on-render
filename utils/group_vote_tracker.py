# ✅ 新模組：group_vote_tracker.py

import re
from linebot.models import TextSendMessage

# 群組統計用的全域變數（可在主程式中引入）
user_votes = {}
stat_active = {}

def handle_group_vote(event, line_bot_api):
    user_msg = event.message.text.strip()
    text = user_msg.replace("【", "").replace("】", "").strip()

    if event.source.type != "group":
        return  # 非群組訊息不處理

    group_id = event.source.group_id

    if group_id not in user_votes:
        user_votes[group_id] = {}
        stat_active[group_id] = False

    if text == "開啟統計":
        user_votes[group_id] = {}
        stat_active[group_id] = True
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="🟢 統計功能已開啟！請大家踴躍 +1 ～如果臨時要取消請喊 -1 ～"))
        return True

    if text == "結束統計":
        if stat_active[group_id]:
            total = sum(user_votes[group_id].values())
            stat_active[group_id] = False
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"🔴 統計已結束，總人數為：{total} 人 🙌"))
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="⚠️ 尚未開啟統計功能。"))
        return True

    if text == "統計人數":
        if stat_active[group_id]:
            total = sum(user_votes[group_id].values())
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"📊 統計進行中，目前為 {total} 人。"))
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="⚠️ 尚未開啟統計功能。"))
        return True

    if stat_active[group_id]:
        plus_match = re.match(r"^\+(\d+)$", text)
        if plus_match:
            count = int(plus_match.group(1))
            user_votes[group_id][len(user_votes[group_id])] = count
            return True
        elif text == "-1":
            if user_votes[group_id]:
                user_votes[group_id].popitem()
            return True

    return False  # 未處理，讓主程式繼續跑其他邏輯
