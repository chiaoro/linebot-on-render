# handlers/doctor_query_handler.py
from linebot.models import TextSendMessage
from utils.google_sheets import get_doctor_info
from utils.session_manager import get_session, set_session, clear_session

def is_doctor_query_trigger(user_id, text, allowed_users):
    return text == "查詢醫師資料（限制使用）" and user_id in allowed_users

def handle_doctor_query(event, line_bot_api, user_id, text, sheet_url):
    session = get_session(user_id)

    # ✅ 第一步：啟動查詢流程
    if text == "查詢醫師資料（限制使用）":
        set_session(user_id, {"step": "waiting_for_doctor_name"})
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請輸入欲查詢的醫師姓名"))
        return True

    # ✅ 第二步：等待使用者輸入姓名
    if session and session.get("step") == "waiting_for_doctor_name":
        doctor_name = text.strip()
        doctor_data = get_doctor_info(sheet_url, doctor_name)

        if doctor_data:
            # ✅ 回傳格式化結果
            response = (
                f"醫師姓名：{doctor_data.get('姓名','')}\n"
                f"出生年月：{doctor_data.get('出生年月','')}\n"
                f"Line ID：{doctor_data.get('Lind ID','')}\n"
                f"性別：{doctor_data.get('性別','')}\n"
                f"年齡：{doctor_data.get('年齡','')}\n"
                f"公務機：{doctor_data.get('公務機','')}\n"
                f"私人手機：{doctor_data.get('私人手機','')}\n"
                f"地址：{doctor_data.get('地址','')}\n"
                f"在澎地址：{doctor_data.get('在澎地址','')}\n"
                f"Email：{doctor_data.get('email','')}\n"
            )
        else:
            response = f"❌ 查無此醫師：{doctor_name}"

        # ✅ 清除狀態
        clear_session(user_id)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=response))
        return True

    return False
