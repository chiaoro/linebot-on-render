# utils/night_shift_fee_generator.py

from utils.line_push import push_text_to_user
import gspread
import os, json
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

SCOPE = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds_dict = json.loads(os.getenv("GOOGLE_CREDENTIALS", "{}"))
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
gc = gspread.authorize(creds)

def generate_night_fee_word():
    # 假設這裡是夜點費資料讀取 + Word生成的邏輯
    # 目前範例只簡單推播一個訊息
    push_text_to_user(
        user_id=os.getenv("All_doctor_group_id"),
        text="✅ 夜點費資料已經成功產出Word文件！"
    )
