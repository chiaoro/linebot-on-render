from flask import Flask, request
from linebot import LineBotApi
from linebot.models import TextSendMessage
from dotenv import load_dotenv
import os

# ✅ 載入 .env 環境變數
load_dotenv()

# ✅ 初始化 Flask 與 LINE Bot API
app = Flask(__name__)
line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))

# ✅ 群組 ID 可從 .env 讀取（你也可以傳入參數指定）
GROUP_ID = os.getenv("LINE_GROUP_ID")

# ✅ 健康檢查
@app.route("/ping", methods=["GET"])
def ping():
    return "推播小秘運作中！", 200

# ✅ 夜點費提醒
@app.route("/night-fee-daily-reminder", methods=["GET"])
def night_fee_daily_reminder():
    try:
        from utils.night_shift_fee import daily_night_fee_reminder
        daily_night_fee_reminder()
        return "✅ 夜點費每日提醒完成", 200
    except Exception as e:
        return f"❌ 夜點費提醒錯誤：{e}", 500

# ✅ 院務會議提醒
@app.route("/meeting-reminder", methods=["GET"])
def meeting_reminder():
    try:
        from utils.meeting_reminder import send_meeting_reminder
        send_meeting_reminder()
        return "✅ 院務會議提醒完成", 200
    except Exception as e:
        return f"❌ 院務會議提醒錯誤：{e}", 500

# ✅ 每月固定推播
@app.route("/monthly-reminder", methods=["GET"])
def monthly_reminder():
    try:
        from utils.monthly_reminder import send_monthly_fixed_reminders
        send_monthly_fixed_reminders()
        return "✅ 固定日期推播完成", 200
    except Exception as e:
        return f"❌ 固定推播錯誤：{e}", 500

# ✅ 重要會議提醒
@app.route("/event-reminder", methods=["GET"])
def event_reminder():
    try:
        from utils.event_reminder import send_important_event_reminder
        send_important_event_reminder()
        return "✅ 重要會議提醒完成", 200
    except Exception as e:
        return f"❌ 重要會議推播錯誤：{e}", 500

# ✅ 每日常規推播
@app.route("/daily-push", methods=["GET"])
def daily_push():
    try:
        from utils.daily_notifier import run_daily_push
        run_daily_push()
        return "✅ 每日推播完成", 200
    except Exception as e:
        return f"❌ 每日推播錯誤：{e}", 500


# ✅ 主程式啟動
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5100))  # 與主機器人分開
    print(f"✅ 推播小秘啟動於 port {port}")
    app.run(host="0.0.0.0", port=port)
