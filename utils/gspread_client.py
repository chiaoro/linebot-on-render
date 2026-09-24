import json
import os
import threading

import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv

load_dotenv()

SCOPE = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
_client = None
_client_lock = threading.Lock()


def get_gspread_client():
    """Return one shared gspread client instead of rebuilding it per request."""
    global _client

    if _client is None:
        with _client_lock:
            if _client is None:
                raw_credentials = os.getenv("GOOGLE_CREDENTIALS")
                if not raw_credentials:
                    raise RuntimeError("GOOGLE_CREDENTIALS is not configured")
                creds_dict = json.loads(raw_credentials)
                creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
                _client = gspread.authorize(creds)
    return _client
