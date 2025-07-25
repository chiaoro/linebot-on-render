# handlers/doctor_query_handler.py
from linebot.models import TextSendMessage
from utils.google_sheets_doctor_query import get_doctor_info
from utils.line_flex_doctor_query import build_doctor_flex

# ✅ 判斷是否觸發
def is_doctor_query_trigger(user_id, text, whitelist):
    return text == "查詢醫師資料（限制使用）" and user_id in whitelist

# ✅ 主流程
def handle_doctor_query(event, line_bot_api):
    user_id = event.source.user_id

    # ✅ 提示使用者輸入醫師姓名
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text="請輸入欲查詢的醫師姓名：")
    )

    # ✅ 後續要在會話管理加 step（簡化，這裡假設下次輸入就是名字）
