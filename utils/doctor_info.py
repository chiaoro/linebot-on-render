import logging

from gspread.exceptions import WorksheetNotFound

from utils.sheet_cache import get_sheet_values_by_url

logger = logging.getLogger(__name__)


class DoctorDirectoryUnavailable(RuntimeError):
    """The doctor mapping sheet could not be read right now."""


def _find_doctor(data, user_id):
    for row in data[1:]:
        if not row:
            continue

        line_id = row[0].strip()
        if line_id != user_id:
            continue

        name = row[1].strip() if len(row) > 1 else ""
        dept = row[2].strip() if len(row) > 2 else ""
        return name or None, dept or "未知"

    return None, None

def get_doctor_info(sheet_url, user_id):
    try:
        data = get_sheet_values_by_url(
            sheet_url,
            "UserMapping",
            ttl_seconds=1800,
            stale_if_error_seconds=86400,
        )
    except WorksheetNotFound:
        logger.error("Doctor directory worksheet is missing")
        raise DoctorDirectoryUnavailable("醫師名單工作表不存在")
    except Exception as e:
        logger.error("Doctor directory read failed: error=%s", type(e).__name__)
        raise DoctorDirectoryUnavailable("醫師名單服務暫時無法使用") from e

    doctor_name, dept = _find_doctor(data, user_id)
    if doctor_name:
        return doctor_name, dept

    # A newly bound user may not be present in the long-lived cache yet.
    try:
        refreshed_data = get_sheet_values_by_url(
            sheet_url,
            "UserMapping",
            ttl_seconds=1800,
            stale_if_error_seconds=0,
            force_refresh=True,
        )
        return _find_doctor(refreshed_data, user_id)
    except Exception as e:
        logger.error("Doctor directory forced refresh failed: error=%s", type(e).__name__)
        raise DoctorDirectoryUnavailable("醫師名單服務暫時無法使用") from e
