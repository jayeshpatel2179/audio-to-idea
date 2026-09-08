import base64
from urllib.parse import quote

import requests

import config

_API_BASE = "https://api.airtable.com/v0"
_CONTENT_BASE = "https://content.airtable.com/v0"

BASE_URL = f"https://airtable.com/{config.AIRTABLE_BASE_ID}"

_HEADERS = {
    "Authorization": f"Bearer {config.AIRTABLE_API_KEY}",
    "Content-Type": "application/json",
}


def create_idea(title: str, video_idea: str, priority: str, status: str = "Not Done") -> str:
    """Create a record and return its record id."""
    url = f"{_API_BASE}/{config.AIRTABLE_BASE_ID}/{quote(config.AIRTABLE_TABLE_NAME)}"
    payload = {
        "fields": {
            "Title": title,
            "Video Idea": video_idea,
            "Priority": priority,
            "Status": status,
        }
    }
    response = requests.post(url, headers=_HEADERS, json=payload, timeout=30)
    response.raise_for_status()
    return response.json()["id"]


def attach_audio(
    record_id: str,
    audio_bytes: bytes,
    filename: str = "voice-note.ogg",
    content_type: str = "audio/ogg",
) -> None:
    """Upload raw audio bytes directly into the record's Audio attachment field."""
    url = f"{_CONTENT_BASE}/{config.AIRTABLE_BASE_ID}/{record_id}/Audio/uploadAttachment"
    payload = {
        "contentType": content_type,
        "file": base64.b64encode(audio_bytes).decode("ascii"),
        "filename": filename,
    }
    response = requests.post(url, headers=_HEADERS, json=payload, timeout=60)
    response.raise_for_status()
