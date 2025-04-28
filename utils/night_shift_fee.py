# utils/night_shift_fee.py

# 用來記錄使用者填夜點費的狀態
night_shift_sessions = {}

# ✅ 啟動夜點費申請流程
def handle_night_shift_request(user_id, user_msg):
    if user_msg == "夜點費申請":
        night_shift_sessions[user_id] = {"step": 0}
        return "📅 請問您本次要申請哪一天？（例如 5/6 上午）"
    return None

# ✅ 持續接收夜點費申請資訊
def continue_night_shift_fee_request(user_id, user_msg):
    session = night_shift_sessions.get(user_id)
    if not session:
        return None  # 沒有在進行中的流程

    if session["step"] == 0:
        session["date"] = user_msg
        session["step"] = 1
        return "🕐 請問班別是什麼？（例如 上午班 / 晚班 / 小夜 / 大夜）"

    elif session["step"] == 1:
        session["shift"] = user_msg
        session["step"] = 2
        return "📝 有沒有備註？（如果沒有請輸入：無）"

    elif session["step"] == 2:
        session["note"] = user_msg
        # 這裡可以把資料寫進試算表（如果你想要的話）
        reply = f"""✅ 已完成申請！
申請日期：{session['date']}
班別：{session['shift']}
備註：{session['note']}
"""
        del night_shift_sessions[user_id]  # 清除狀態
        return reply

    return None
