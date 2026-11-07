"""Runtime settings loaded from the environment.

The API key is never stored in source. Copy .env.example to .env and set
OPENAI_API_KEY there, or export it in the shell before starting the server.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


def get_settings() -> dict:
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").strip()
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"
    return {
        "api_key": os.getenv("OPENAI_API_KEY", "").strip(),
        "base_url": base_url.rstrip("/"),
        "model": model,
    }


def get_postgres_settings() -> dict:
    """Connection fields come from the environment. Nothing here is a secret literal."""
    port = os.getenv("POSTGRES_PORT", "5432").strip() or "5432"
    settings = {
        "host": os.getenv("POSTGRES_HOST", "127.0.0.1").strip() or "127.0.0.1",
        "port": int(port),
        "dbname": os.getenv("POSTGRES_DB", "").strip(),
        "user": os.getenv("POSTGRES_USER", "").strip(),
    }
    password = os.getenv("POSTGRES_PASSWORD", "").strip()
    if password:
        settings["password"] = password
    return settings
