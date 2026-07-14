from linebot.models import TextSendMessage
from utils.state_manager import get_state, set_state, clear_state
from utils.meeting_leave_menu import get_meeting_leave_menu, get_meeting_leave_success
from utils.doctor_info import get_doctor_info
from utils.command_texts import MENU_COMMANDS
import requests

# ✅ Webhook URL（請假資料送出處）
WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbyk8tqbMREdzaWpwJ5ZE0CJsC_0JmsE1QRW1-S0ALvYVYuCQxlVELCI8GrvpUjF6pPg/exec"

# ✅ 醫師對照表網址（查姓名與科別）
DOCTOR_SHEET_URL = "https://docs.google.com/spreadsheets/d/1fHf5XlbvLMd6ytAh_t8Bsi5ghToiQHZy1NlVfEG7VIo/edit"








def log_meeting_reply(user_id, doctor_name, dept, status, reason):
    payload = {
        "user_id": user_id,
        "doctor_name": doctor_name,
        "department": dept,
        "status": status,
        "reason": reason
    }

    print(f"[DEBUG] 🚀 準備送出資料：{payload}")

    try:
        response = requests.post(WEBHOOK_URL, json=payload)
        response.raise_for_status()
        print(f"[SUCCESS] GAS 回應：{response.text}")
    except Exception as e:
        print(f"[ERROR] Webhook 傳送失敗：{e}")
        raise e

def handle_meeting_leave(event, user_id, text, line_bot_api):
    raw_text = event.message.text.strip()

    # ✅ 初次進入：觸發請假流程
    if raw_text == "院務會議請假":
        print(f"[DEBUG] 觸發院務會議請假，user_id={user_id}")
        set_state(user_id, "ASK_LEAVE")
        line_bot_api.reply_message(event.reply_token, get_meeting_leave_menu())
        return True

    state = get_state(user_id)

    # Let new menu commands switch away from a stale meeting-leave flow.
    if state in ["ASK_LEAVE", "ASK_REASON"] and raw_text in MENU_COMMANDS:
        clear_state(user_id)
        return False

    # ✅ 使用者點選出席或請假
    if state == "ASK_LEAVE":
        if raw_text == "我要出席院務會議":
            try:
                doctor_name, dept = get_doctor_info(DOCTOR_SHEET_URL, user_id)
                if not doctor_name:
                    raise ValueError("查無對應醫師資訊")
                log_meeting_reply(user_id, doctor_name, dept, "出席", "")
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="✅ 您已回覆出席，請當天準時與會。"))
            except Exception as e:
                print(f"[ERROR] 出席紀錄失敗：{e}")
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="⚠️ 查無醫師資訊或系統錯誤，請聯絡巧柔"))
            clear_state(user_id)
        elif raw_text == "我要請假院務會議":
            set_state(user_id, "ASK_REASON")
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="📝 請輸入您無法出席的原因："))
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="⚠️ 請點選上方按鈕回覆"))
        return True

    # ✅ 請假者輸入原因
    if state == "ASK_REASON":
        reason = raw_text
        try:
            doctor_name, dept = get_doctor_info(DOCTOR_SHEET_URL, user_id)
            if not doctor_name:
                raise ValueError("查無對應醫師資訊")
            log_meeting_reply(user_id, doctor_name, dept, "請假", reason)
            print(f"[DEBUG] 已紀錄請假：{doctor_name}（{dept}） - {reason}")
            line_bot_api.reply_message(event.reply_token, get_meeting_leave_success(reason))
        except Exception as e:
            print(f"[ERROR] 請假紀錄失敗：{e}")
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="⚠️ 查無醫師資訊或系統錯誤，請聯絡巧柔"))
        clear_state(user_id)
        return True

    return False
