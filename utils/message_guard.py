# utils/message_guard.py

def should_ignore_message(source_type, text):
    """是否忽略訊息：只處理私訊或明確開頭指令"""
    trigger_keywords = ["我要調診", "我要休診", "我要代診", "我要加診", "值班調換", "值班代理", "夜點費申請"]
    if source_type != 'user' and not any(text.startswith(k) for k in trigger_keywords):
        print(f"❌ 忽略群組內非關鍵字訊息：{text}")
        return True
    return False


def handle_direct_command(text, user_id, line_bot_api, event, user_sessions):
    """處理值班調換 / 代理的直接啟動指令（不進三步驟流程）"""
    if text == "值班調換" or text == "值班代理":
        action_type = "值班調換" if text == "值班調換" else "值班代理"
        user_sessions[user_id] = {"step": 0, "type": action_type}
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="🧑‍⚕️ 請輸入您的姓名"))
        return True
    return False
