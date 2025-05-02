# utils/flex_templates.py

def get_adjustment_bubble(original, method, reason):
    """調診／代診結果 Flex Bubble"""
    return {
        "type": "bubble",
        "header": {
            "type": "box",
            "layout": "vertical",
            "contents": [{
                "type": "text",
                "text": "✅ 門診調整已送出",
                "weight": "bold",
                "color": "#1DB446",
                "size": "lg"
            }]
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "contents": [
                {"type": "text", "text": f"📅 原門診：{original}", "wrap": True},
                {"type": "text", "text": f"🛠️ 處理方式：{method}", "wrap": True},
                {"type": "text", "text": f"📝 調整原因：{reason}", "wrap": True}
            ]
        },
        "footer": {
            "type": "box",
            "layout": "horizontal",
            "contents": [{
                "type": "text",
                "text": "如有誤請洽醫療部秘書",
                "size": "sm",
                "color": "#aaaaaa"
            }]
        }
    }


def get_duty_swap_bubble(shift_type, original_doctor, original_date, target_doctor, swap_date, reason):
    """值班調換結果 Flex Bubble"""
    return {
        "type": "bubble",
        "header": {
            "type": "box",
            "layout": "vertical",
            "contents": [{
                "type": "text",
                "text": "✅ 值班調換已送出",
                "weight": "bold",
                "color": "#007AFF",
                "size": "lg"
            }]
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "contents": [
                {"type": "text", "text": f"🧑‍⚕️ 原值班醫師：{original_doctor}", "wrap": True},
                {"type": "text", "text": f"📅 原值班日：{original_date}", "wrap": True},
                {"type": "text", "text": f"🔁 班別：{shift_type}", "wrap": True},
                {"type": "text", "text": f"🤝 對調醫師：{target_doctor}", "wrap": True},
                {"type": "text", "text": f"📅 調換至：{swap_date}", "wrap": True},
                {"type": "text", "text": f"📝 原因：{reason}", "wrap": True}
            ]
        },
        "footer": {
            "type": "box",
            "layout": "horizontal",
            "contents": [{
                "type": "text",
                "text": "如有誤請洽醫療部秘書",
                "size": "sm",
                "color": "#aaaaaa"
            }]
        }
    }






ChatGPT 說：
太好了！我這就幫你把「值班調換」與「值班代理」的流程也改成穩定寫法：

✅ 先 reply 簡訊確認（避免 reply token 過期）
✅ 再 push Flex Bubble 呈現結果（圖文清楚有質感）

✅ 假設你的流程如下（四步驟）：
以「值班調換」為例，流程步驟：
step	問題內容	儲存欄位
0	醫師姓名	original_doctor
1	原值班班別與日期	shift_type, original_date
2	對方醫師與調換日期	target_doctor, swap_date
3	原因	reason

✅ 完整改寫：值班調換流程（含 push Bubble）
請將原本的「值班調換流程」邏輯區塊，換成以下這段：

python
複製
編輯
from linebot.models import FlexSendMessage
from utils.flex_templates import get_duty_swap_bubble

if text == "值班調換":
    user_sessions[user_id] = {"step": 0, "type": "值班調換"}
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text="👨‍⚕️ 請輸入您的姓名"))
    return

if user_id in user_sessions and user_sessions[user_id].get("type") == "值班調換":
    session = user_sessions[user_id]

    if session["step"] == 0:
        session["original_doctor"] = text
        session["step"] = 1
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="📅 請輸入原值班班別與日期（例如：夜班 5/10）"))

    elif session["step"] == 1:
        # 拆解班別與日期
        try:
            shift_type, date = text.split(" ")
            session["shift_type"] = shift_type
            session["original_date"] = date
        except:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="⚠️ 請用正確格式輸入，例如：夜班 5/10"))
            return

        session["step"] = 2
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="🔁 請輸入對調醫師姓名與調換日期（例如：李大華 5/17）"))

    elif session["step"] == 2:
        try:
            name, date = text.split(" ")
            session["target_doctor"] = name
            session["swap_date"] = date
        except:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="⚠️ 請用正確格式輸入，例如：李大華 5/17"))
            return

        session["step"] = 3
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="📝 請輸入調換原因"))

    elif session["step"] == 3:
        session["reason"] = text

        webhook_url = "https://script.google.com/macros/s/你的_webhook_url/exec"
        payload = {
            "request_type": "值班調換",
            "original_doctor": session["original_doctor"],
            "shift_type": session["shift_type"],
            "original_date": session["original_date"],
            "target_doctor": session["target_doctor"],
            "swap_date": session["swap_date"],
            "reason": session["reason"]
        }

        # ✅ 先 reply 表示成功收到
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="📨 已收到申請，稍後會送出調換通知")
        )

        try:
            requests.post(webhook_url, json=payload)

            bubble = get_duty_swap_bubble(
                shift_type=session["shift_type"],
                original_doctor=session["original_doctor"],
                original_date=session["original_date"],
                target_doctor=session["target_doctor"],
                swap_date=session["swap_date"],
                reason=session["reason"]
            )

            line_bot_api.push_message(
                user_id,
                FlexSendMessage(alt_text="值班調換通知", contents=bubble)
            )

        except Exception as e:
            print("❌ webhook 發送失敗：", str(e))
            line_bot_api.push_message(user_id, TextSendMessage(
                text="⚠️ 系統提交失敗，請稍後再試"
            ))

        del user_sessions[user_id]
    return
✅ 你還需要：
在 utils/flex_templates.py 補上：
python
複製
編輯
def get_duty_swap_bubble(shift_type, original_doctor, original_date, target_doctor, swap_date, reason):
    return {
        "type": "bubble",
        "header": {
            "type": "box",
            "layout": "vertical",
            "contents": [{
                "type": "text",
                "text": "✅ 值班調換已送出",
                "weight": "bold",
                "color": "#007AFF",
                "size": "lg"
            }]
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "contents": [
                {"type": "text", "text": f"🧑‍⚕️ 醫師：{original_doctor}", "wrap": True},
                {"type": "text", "text": f"📅 原值班：{shift_type} {original_date}", "wrap": True},
                {"type": "text", "text": f"🤝 對調醫師：{target_doctor}", "wrap": True},
                {"type": "text", "text": f"📅 調換至：{swap_date}", "wrap": True},
                {"type": "text", "text": f"📝 原因：{reason}", "wrap": True}
            ]
        },
        "footer": {
            "type": "box",
            "layout": "horizontal",
            "contents": [{
                "type": "text",
                "text": "如有誤請洽醫療部秘書",
                "size": "sm",
                "color": "#aaaaaa"
            }]
        }
    }
