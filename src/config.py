import os
from dotenv import load_dotenv

load_dotenv()

# API Keys and IDs
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY") or ""
NOTION_API_KEY = os.getenv("NOTION_API_KEY") or ""
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID", "86585ef1-f1a6-4ab4-b183-c4f78a452e21")

# Notion API version
NOTION_VERSION = "2022-06-28"

# Google AI Studio Free Tier Quotas & Model Metadata
MODEL_METADATA = {
    "gemini-3.5-flash-lite": {
        "display_name": "Gemini 3.5 Flash Lite",
        "description": "Leggyorsabb és leggazdaságosabb modell, ideális leiratokhoz.",
        "input_token_limit": 1_048_576,
        "output_token_limit": 65_536,
        "rpm": 15,
        "tpm": 1_000_000,
        "rpd": 1_500,
        "pricing": "Free of charge (Free tier)"
    },
    "gemini-3.5-flash": {
        "display_name": "Gemini 3.5 Flash",
        "description": "Kiváló egyensúly sebesség és mély szövegértés között.",
        "input_token_limit": 1_048_576,
        "output_token_limit": 65_536,
        "rpm": 15,
        "tpm": 1_000_000,
        "rpd": 1_500,
        "pricing": "Free of charge (Free tier)"
    },
    "gemini-3.8-flash": {
        "display_name": "Gemini 3.8 Flash",
        "description": "Legújabb fejlesztésű Flash modell magas logikai képességekkel.",
        "input_token_limit": 1_048_576,
        "output_token_limit": 65_536,
        "rpm": 15,
        "tpm": 1_000_000,
        "rpd": 1_500,
        "pricing": "Free of charge (Free tier)"
    }
}

DEFAULT_MODEL = "gemini-3.5-flash-lite"
PLAN_INFO_URL = "https://aistudio.google.com/plan_information"
DEFAULT_PLAYLIST_URL = os.getenv("DEFAULT_PLAYLIST_URL", "https://www.youtube.com/playlist?list=PLr-48e7JNg_5abe8pP-7fZCMM2KThq61z")
DEFAULT_LANGUAGE = "A videó eredeti nyelve"
