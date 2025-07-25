# handlers/doctor_query_handler.py

from linebot.models import TextSendMessage
from utils.session_manager import set_session, get_session, clear_session
from utils.google_sheets import get_doctor_info

# ✅ 觸發判斷（保留給 app.py 用，非必要可省略）
def is_doctor_query_trigger(user_id, text, allowed_users):
    return user_id in allowed_users and text in ["查詢醫師資料（限制使用）", "醫師資訊查詢（限制使用）"]

# ✅ 啟動醫師查詢流程
def start_doctor_query(user_id):
    set_session(user_id, {"type": "doctor_query", "step": 1})

# ✅ 是否處於查詢狀態
def is_in_doctor_query_session(user_id):
    session = get_session(user_id)
    return session.get("type") == "doctor_query" and session.get("step") == 1

# ✅ 處理姓名輸入階段（step 1）
def process_doctor_name(user_id, doctor_name, line_bot_api, reply_token):
    clear_session(user_id)  # 查詢後直接清除狀態
    values = get_doctor_info(doctor_name)

    if not values:
        line_bot_api.reply_message(reply_token, TextSendMessage(text=f"❌ 查無醫師：{doctor_name}"))
        return

    result = format_doctor_info(values)
    line_bot_api.reply_message(reply_token, TextSendMessage(text=result))

# ✅ 整合資訊格式化

def format_doctor_info(data):
    keys = [
        "姓名", "出生年月", "Line ID", "性別", "年齡", "公務機",
        "私人手機", "地址", "在澎地址", "email",
        "緊急連絡人姓名", "緊急連絡人關係", "緊急連絡人電話"
    ]

    result = ["三軍總醫院澎湖分院醫師資料查詢"]
    for i in range(len(keys)):
        value = data[i] if i < len(data) and data[i] else ""
        result.append(f"{keys[i]}：{value}")

    return "\n".join(result)


# ✅ 主處理函式

def handle_doctor_query(event, line_bot_api, user_id, text, sheet_url):
    from app import ALLOWED_USER_IDS  # 為了 access 白名單

    # Step 0: 觸發起始查詢
    if text in ["查詢醫師資料（限制使用）", "醫師資訊查詢（限制使用）"]:
        if user_id not in ALLOWED_USER_IDS:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="⚠️ 你沒有使用此功能的權限"))
            return True
        start_doctor_query(user_id)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請輸入欲查詢的醫師姓名"))
        return True

    # Step 1: 使用者正在輸入醫師姓名
    if is_in_doctor_query_session(user_id):
        process_doctor_name(user_id, text, line_bot_api, event.reply_token)
        return True

    return False
