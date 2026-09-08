import os

from dotenv import load_dotenv

load_dotenv()

REQUIRED_VARS = [
    "TELEGRAM_BOT_TOKEN",
    "DEEPGRAM_API_KEY",
    "OPENAI_API_KEY",
    "AIRTABLE_API_KEY",
    "AIRTABLE_BASE_ID",
]

_missing = [name for name in REQUIRED_VARS if not os.environ.get(name)]
if _missing:
    raise RuntimeError(
        f"Missing required environment variables: {', '.join(_missing)}. "
        "Copy .env.example to .env and fill in the values."
    )

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
DEEPGRAM_API_KEY = os.environ["DEEPGRAM_API_KEY"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
DEEPGRAM_MODEL = os.environ.get("DEEPGRAM_MODEL", "nova-2")
AIRTABLE_API_KEY = os.environ["AIRTABLE_API_KEY"]
AIRTABLE_BASE_ID = os.environ["AIRTABLE_BASE_ID"]
AIRTABLE_TABLE_NAME = os.environ.get("AIRTABLE_TABLE_NAME", "Video Ideas")
