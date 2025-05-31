import gspread
from oauth2client.service_account import ServiceAccountCredentials

def get_doctor_info(sheet_url, user_id):
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
    client = gspread.authorize(creds)

    sheet = client.open_by_url(sheet_url).worksheet("UserMapping")
    data = sheet.get_all_values()

    for row in data[1:]:
        if row[0] == user_id:
            return row[1], row[2]  # 回傳 醫師姓名、科別

    return "未知", "未知"
