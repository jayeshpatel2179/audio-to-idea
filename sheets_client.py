import json

import gspread
from google.oauth2.service_account import Credentials

import config

_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

HEADER = ["Title", "Video Idea", "Priority", "Status"]

if config.GOOGLE_SERVICE_ACCOUNT_JSON:
    _service_account_info = json.loads(config.GOOGLE_SERVICE_ACCOUNT_JSON)
    _creds = Credentials.from_service_account_info(_service_account_info, scopes=_SCOPES)
else:
    _creds = Credentials.from_service_account_file(config.GOOGLE_SERVICE_ACCOUNT_FILE, scopes=_SCOPES)
_gc = gspread.authorize(_creds)
_sheet = _gc.open_by_key(config.GOOGLE_SHEET_ID).worksheet(config.GOOGLE_SHEET_NAME)


def ensure_header() -> None:
    """Write the header row only if the sheet is completely empty."""
    if not _sheet.get_all_values():
        _sheet.append_row(HEADER, value_input_option="USER_ENTERED")


def append_idea(title: str, video_idea: str, priority: str, status: str = "Not Done") -> None:
    _sheet.append_row([title, video_idea, priority, status], value_input_option="USER_ENTERED")
