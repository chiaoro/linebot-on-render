# handlers/doctor_query_handler.py
from utils.google_sheets import get_doctor_info
from utils.session_manager import set_session, get_session, clear_session
from linebot.models import TextSendMessage

def start_doctor_query(user_id):
    set_session(user_id, {"type": "doctor_query", "step": 1})

def is_in_doctor_query_session(user_id):
    session = get_session(user_id)
    return session and session.get("type") == "doctor_query"

def process_doctor_name(user_id, doctor_name, line_bot_api, reply_token):
    info = get_doctor_info(doctor_name)
    if info:
        message = format_doctor_info(info)
    else:
        message = f"❌ 找不到醫師：{doctor_name}"
    line_bot_api.reply_message(reply_token, TextSendMessage(text=message))
    clear_session(user_id)

def format_doctor_info(info):
    return (
        f"姓名：{info.get('姓名','')}\n"
        f"出生年月：{info.get('出生年月','')}\n"
        f"性別：{info.get('性別','')}\n"
        f"年齡：{info.get('年齡','')}\n"
        f"公務機：{info.get('公務機','')}\n"
        f"私人手機：{info.get('私人手機','')}\n"
        f"地址：{info.get('地址','')}\n"
        f"在澎地址：{info.get('在澎地址','')}\n"
        f"email：{info.get('email','')}\n"
        f"緊急聯絡人姓名：{info.get('緊急聯絡人姓名','')}\n"
        f"緊急聯絡人關係：{info.get('緊急聯絡人關係','')}\n"
        f"緊急聯絡人電話：{info.get('緊急聯絡人電話','')}"
    )
