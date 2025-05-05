#utils/state_manager_google.py
from utils.gspread_client import get_gspread_client

# ✅ 替換成實際表單網址與分頁名稱
STATE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1-mI71sC7TE-f8Gb9YPddhVGJrozKxLIdJlSBf2khJsA/edit"
STATE_SHEET_NAME = "使用者狀態"

def get_state(user_id):
    try:
        gc = get_gspread_client()
        sheet = gc.open_by_url(STATE_SHEET_URL).worksheet(STATE_SHEET_NAME)
        records = sheet.get_all_records()
        for row in records:
            if row.get("使用者ID") == user_id:
                return row.get("狀態")
        return None
    except Exception as e:
        print(f"❌ get_state 發生錯誤：{e}")
        return None

def set_state(user_id, state):
    try:
        gc = get_gspread_client()
        sheet = gc.open_by_url(STATE_SHEET_URL).worksheet(STATE_SHEET_NAME)
        records = sheet.get_all_records()
        for i, row in enumerate(records):
            if row.get("使用者ID") == user_id:
                sheet.update_cell(i + 2, 2, state)  # 第 2 欄為「狀態」
                return
        sheet.append_row([user_id, state])
    except Exception as e:
        print(f"❌ set_state 發生錯誤：{e}")

def clear_state(user_id):
    try:
        gc = get_gspread_client()
        sheet = gc.open_by_url(STATE_SHEET_URL).worksheet(STATE_SHEET_NAME)
        records = sheet.get_all_records()
        for i, row in enumerate(records):
            if row.get("使用者ID") == user_id:
                sheet.delete_rows(i + 2)
                return
    except Exception as e:
        print(f"❌ clear_state 發生錯誤：{e}")

# ✅ 測試函式（除錯用）
def log_something():
    gc = get_gspread_client()
    sheet = gc.open_by_url(STATE_SHEET_URL).worksheet(STATE_SHEET_NAME)
    sheet.append_row(["hello", "world"])



# ✅ 替換成實際表單網址與分頁名稱
STATE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1-mI71sC7TE-f8Gb9YPddhVGJrozKxLIdJlSBf2khJsA/edit"
STATE_SHEET_NAME = "使用者狀態"

def get_state(user_id):
    try:
        gc = get_gspread_client()
        sheet = gc.open_by_url(STATE_SHEET_URL).worksheet(STATE_SHEET_NAME)
        records = sheet.get_all_records()
        for row in records:
            if row.get("使用者ID") == user_id:
                return row.get("狀態")
        return None
    except Exception as e:
        print(f"❌ get_state 發生錯誤：{e}")
        return None

def set_state(user_id, state):
    try:
        gc = get_gspread_client()
        sheet = gc.open_by_url(STATE_SHEET_URL).worksheet(STATE_SHEET_NAME)
        records = sheet.get_all_records()
        for i, row in enumerate(records):
            if row.get("使用者ID") == user_id:
                sheet.update_cell(i + 2, 2, state)  # 第 2 欄為「狀態」
                return
        sheet.append_row([user_id, state])
    except Exception as e:
        print(f"❌ set_state 發生錯誤：{e}")

def clear_state(user_id):
    try:
        gc = get_gspread_client()
        sheet = gc.open_by_url(STATE_SHEET_URL).worksheet(STATE_SHEET_NAME)
        records = sheet.get_all_records()
        for i, row in enumerate(records):
            if row.get("使用者ID") == user_id:
                sheet.delete_rows(i + 2)
                return
    except Exception as e:
        print(f"❌ clear_state 發生錯誤：{e}")

# ✅ 測試函式（除錯用）
def log_something():
    gc = get_gspread_client()
    sheet = gc.open_by_url(STATE_SHEET_URL).worksheet(STATE_SHEET_NAME)
    sheet.append_row(["hello", "world"])




from utils.gspread_client import get_gspread_client

# ✅ 替換成實際表單網址與分頁名稱
STATE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1-mI71sC7TE-f8Gb9YPddhVGJrozKxLIdJlSBf2khJsA/edit"
STATE_SHEET_NAME = "使用者狀態"

def get_state(user_id):
    try:
        gc = get_gspread_client()
        sheet = gc.open_by_url(STATE_SHEET_URL).worksheet(STATE_SHEET_NAME)
        records = sheet.get_all_records()
        for row in records:
            if row.get("使用者ID") == user_id:
                return row.get("狀態")
        return None
    except Exception as e:
        print(f"❌ get_state 發生錯誤：{e}")
        return None

def set_state(user_id, state):
    try:
        gc = get_gspread_client()
        sheet = gc.open_by_url(STATE_SHEET_URL).worksheet(STATE_SHEET_NAME)
        records = sheet.get_all_records()
        for i, row in enumerate(records):
            if row.get("使用者ID") == user_id:
                sheet.update_cell(i + 2, 2, state)  # 第 2 欄為「狀態」
                return
        sheet.append_row([user_id, state])
    except Exception as e:
        print(f"❌ set_state 發生錯誤：{e}")

def clear_state(user_id):
    try:
        gc = get_gspread_client()
        sheet = gc.open_by_url(STATE_SHEET_URL).worksheet(STATE_SHEET_NAME)
        records = sheet.get_all_records()
        for i, row in enumerate(records):
            if row.get("使用者ID") == user_id:
                sheet.delete_rows(i + 2)
                return
    except Exception as e:
        print(f"❌ clear_state 發生錯誤：{e}")

# ✅ 測試函式（除錯用）
def log_something():
    gc = get_gspread_client()
    sheet = gc.open_by_url(STATE_SHEET_URL).worksheet(STATE_SHEET_NAME)
    sheet.append_row(["hello", "world"])
