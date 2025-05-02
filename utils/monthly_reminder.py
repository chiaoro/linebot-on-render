import os, json, gspread
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv
from utils.line_push import push_text_to_group

load_dotenv()

# ✅ Google Sheets 認證
SCOPE = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds_dict = json.loads(os.getenv("GOOGLE_CREDENTIALS"))
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
gc = gspread.authorize(creds)

# ✅ 固定日期推播紀錄表
FIXED_PUSH_URL = "https://docs.google.com/spreadsheets/d/1XpX1l7Uf93XWNEYdZsHx-3IXpPf4Sb9Zl0ARGa4Iy5c/edit"
WORKSHEET_NAME = "固定日期推播"
fixed_sheet = gc.open_by_url(FIXED_PUSH_URL).worksheet(WORKSHEET_NAME)

def send_monthly_fixed_reminders():
    today = datetime.now().strftime("%Y-%m-%d")
    data = fixed_sheet.get_all_records()
    header = fixed_sheet.row_values(1)

    try:
        status_col_idx = header.index("提醒狀態") + 1  # D欄
    except ValueError:
        print("❌ 無法找到『提醒狀態』欄位，請確認試算表第一列標題")
        return

    for idx, record in enumerate(data, start=2):  # 從第2列開始（跳過標題列）
        push_date = str(record.get("日期")).strip()
        message = str(record.get("推播項目")).strip()
        group = str(record.get("推播對象")).strip()
        status = str(record.get("提醒狀態")).strip()

        if push_date == today and status != "已推播":
            # ✅ 判斷推播對象群組 ID
            if group == "內科":
                group_id = os.getenv("internal_medicine_group_id")
            elif group == "外科":
                group_id = os.getenv("surgery_group_id")
            else:
                group_id = os.getenv("All_doctor_group_id")

            # ✅ 推播與紀錄
            if group_id:
                try:
                    push_text_to_group(group_id, f"📣{message}")
                    print(f"✅ 已推播：{message} → {group}")
                    fixed_sheet.update_cell(idx, status_col_idx, "已推播")
                except Exception as e:
                    print(f"❌ 推播或寫入失敗：第{idx}列，錯誤：{e}")
            else:
                print(f"⚠️ 找不到對應群組環境變數：{group}")
