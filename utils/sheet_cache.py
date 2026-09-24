import logging
import threading
import time

from gspread.exceptions import SpreadsheetNotFound, WorksheetNotFound
from requests.exceptions import RequestException

from utils.gspread_client import get_gspread_client

logger = logging.getLogger(__name__)

_values_cache = {}
_locks = {}
_locks_guard = threading.Lock()


def _get_key_lock(key):
    with _locks_guard:
        return _locks.setdefault(key, threading.Lock())


def _is_retryable(exc):
    if isinstance(exc, (SpreadsheetNotFound, WorksheetNotFound)):
        return False
    if isinstance(exc, (RequestException, OSError, TimeoutError)):
        return True

    response = getattr(exc, "response", None)
    status_code = getattr(response, "status_code", None)
    return status_code == 429 or (status_code is not None and status_code >= 500)


def get_sheet_values_by_url(
    sheet_url,
    worksheet_name,
    ttl_seconds=300,
    stale_if_error_seconds=3600,
    max_attempts=3,
    force_refresh=False,
):
    """Read a worksheet with single-flight refresh, retry, and stale fallback."""
    key = (sheet_url, worksheet_name)
    now = time.monotonic()
    cached = _values_cache.get(key)

    if not force_refresh and cached and now - cached["time"] < ttl_seconds:
        return cached["values"]

    with _get_key_lock(key):
        now = time.monotonic()
        cached = _values_cache.get(key)
        if not force_refresh and cached and now - cached["time"] < ttl_seconds:
            return cached["values"]

        last_error = None
        for attempt in range(1, max_attempts + 1):
            try:
                worksheet = cached.get("worksheet") if cached else None
                if worksheet is None:
                    gc = get_gspread_client()
                    worksheet = gc.open_by_url(sheet_url).worksheet(worksheet_name)

                values = worksheet.get_all_values()
                _values_cache[key] = {
                    "time": time.monotonic(),
                    "values": values,
                    "worksheet": worksheet,
                }
                return values
            except Exception as exc:
                last_error = exc
                retryable = _is_retryable(exc)
                logger.warning(
                    "Google Sheet refresh failed: worksheet=%s attempt=%s/%s error=%s",
                    worksheet_name,
                    attempt,
                    max_attempts,
                    type(exc).__name__,
                )
                if not retryable or attempt >= max_attempts:
                    break
                time.sleep(0.2 * attempt)

        if cached and stale_if_error_seconds > 0:
            age = time.monotonic() - cached["time"]
            if age < stale_if_error_seconds:
                logger.warning(
                    "Using stale Google Sheet cache after refresh failure: worksheet=%s age_seconds=%d",
                    worksheet_name,
                    age,
                )
                return cached["values"]

        raise last_error


def clear_sheet_values_cache():
    _values_cache.clear()
