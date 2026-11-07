"""Shared template setup and sidebar data."""

from pathlib import Path

from fastapi.templating import Jinja2Templates

from backend.db import rows

HTML_DIR = Path(__file__).resolve().parent.parent.parent / "ui-html"
templates = Jinja2Templates(directory=str(HTML_DIR))


def shell(active: str) -> dict:
    return {
        "active": active,
        "chats": rows("SELECT id, title, preview, time_label FROM chats ORDER BY id"),
    }
