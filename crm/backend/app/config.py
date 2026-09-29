"""Runtime settings. Secrets stay in the environment, never in source."""

import os
from pathlib import Path

from dotenv import load_dotenv

CRM_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(CRM_ROOT / ".env", override=False)

DEFAULT_DATABASE_URL = "sqlite:///" + (CRM_ROOT / "data" / "crm.sqlite").as_posix()


def get_settings():
    token = os.environ.get("CRM_API_TOKEN", "").strip()
    origins = os.environ.get(
        "CORS_ORIGINS",
        "http://127.0.0.1:5174,http://localhost:5174",
    )
    return {
        "database_url": os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL).strip(),
        "api_token": token,
        "cors_origins": [origin.strip() for origin in origins.split(",") if origin.strip()],
        "seed_on_start": os.environ.get("SEED_ON_START", "").strip() == "1",
    }
