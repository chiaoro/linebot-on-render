# handlers/doctor_query_handler.py

from linebot.models import TextSendMessage
from utils.session_manager import user_sessions
from utils.google_sheets import get_doctor_info

# ✅ 醫師查詢流程
def handle_doctor_query(event, line_bot_api, user_id, text, sheet_url):
    # === Step 1：啟動查詢 ===
    if text in ["查詢醫師資料（限制使用）", "醫師資訊查詢（限制使用）"]:
        from app import ALLOWED_USER_IDS  # 從 app.py 引用白名單
        if user_id not in ALLOWED_USER_IDS:
            print(f"❌ 用戶 {user_id} 嘗試使用醫師查詢，但不在白名單")
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="⚠️ 你沒有使用此功能的權限"))
            return True

        # ✅ 設定 session 狀態
        user_sessions[user_id] = {"step": 1}
        print(f"✅ 啟動醫師查詢流程，user_id={user_id}")
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請輸入欲查詢的醫師姓名"))
        return True

    # === Step 2：輸入醫師姓名 ===
    if user_sessions.get(user_id, {}).get("step") == 1:
        doctor_name = text.strip()
        print(f"🔍 查詢醫師姓名：{doctor_name}")

        # ✅ 從 Google Sheet 抓資料
        doctor_info = get_doctor_info(sheet_url, doctor_name)

        if doctor_info:
            reply_text = format_doctor_info(doctor_info)
        else:
            reply_text = f"❌ 找不到醫師：{doctor_name}，請確認姓名是否正確"

        # ✅ 回覆並清除 session
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))
        user_sessions.pop(user_id, None)
        return True

    return False


# ✅ 格式化醫師資訊
def format_doctor_info(info):
    """
    info: dict, e.g.
    {
        '姓名': '王大明',
        '出生年月': '1984/01/16',
        '性別': '男',
        '年齡': '41',
        '公務機': '15859',
        '私人手機': '0909394969',
        '地址': '高雄市...',
        '在澎地址': '馬公市...',
        'email': 'example@gmail.com',
        '緊急聯絡人姓名': '王小明',
        '緊急聯絡人關係': '父子',
        '緊急聯絡人電話': '0912345678'
    }
    """
    fields = [
        ("姓名", info.get("姓名", "")),
        ("出生年月", info.get("出生年月", "")),
        ("性別", info.get("性別", "")),
        ("年齡", info.get("年齡", "")),
        ("公務機", info.get("公務機", "")),
        ("私人手機", info.get("私人手機", "")),
        ("地址", info.get("地址", "")),
        ("在澎地址", info.get("在澎地址", "")),
        ("Email", info.get("email", "")),
        ("緊急聯絡人姓名", info.get("緊急聯絡人姓名", "")),
        ("緊急聯絡人關係", info.get("緊急聯絡人關係", "")),
        ("緊急聯絡人電話", info.get("緊急聯絡人電話", "")),
    ]

    return "\n".join([f"{k}：{v}" for k, v in fields if v])
