import time

from utils.gspread_client import get_gspread_client

_values_cache = {}


def get_sheet_values_by_url(sheet_url, worksheet_name, ttl_seconds=300):
    key = (sheet_url, worksheet_name)
    now = time.time()
    cached = _values_cache.get(key)

    if cached and now - cached["time"] < ttl_seconds:
        return cached["values"]

    gc = get_gspread_client()
    sheet = gc.open_by_url(sheet_url).worksheet(worksheet_name)
    values = sheet.get_all_values()
    _values_cache[key] = {"time": now, "values": values}
    return values


def clear_sheet_values_cache():
    _values_cache.clear()
