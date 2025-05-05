import gspread
from utils.gspread_client import get_gspread_client


# ✅ 替換成你的實際網址
STATE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1-mI71sC7TE-f8Gb9YPddhVGJrozKxLIdJlSBf2khJsA/edit"
STATE_SHEET_NAME = "使用者狀態"
DOCTOR_SHEET_URL = "https://docs.google.com/spreadsheets/d/1fHf5XlbvLMd6ytAh_t8Bsi5ghToiQHZy1NlVfEG7VIo/edit"

def get_state(user_id):
    gc = get_gspread_client()
    sheet = gc.open_by_url(STATE_SHEET_URL).sheet1
    records = sheet.get_all_records()
    for row in records:
        if row['使用者ID'] == user_id:
            return row['狀態']
    return None

def set_state(user_id, state):
    gc = get_gspread_client()
    sheet = gc.open_by_url(STATE_SHEET_URL).sheet1
    records = sheet.get_all_records()
    for i, row in enumerate(records):
        if row['使用者ID'] == user_id:
            sheet.update_cell(i + 2, 2, state)  # 第 2 欄是狀態
            return
    sheet.append_row([user_id, state])

def clear_state(user_id):
    gc = get_gspread_client()
    sheet = gc.open_by_url(STATE_SHEET_URL).sheet1
    records = sheet.get_all_records()
    for i, row in enumerate(records):
        if row['使用者ID'] == user_id:
            sheet.delete_rows(i + 2)
            return


def log_something():
    gc = get_gspread_client()
    sheet = gc.open_by_url(...).worksheet("記錄表")
    sheet.append_row(["hello", "world"])
