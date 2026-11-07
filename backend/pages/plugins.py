"""Plugins page. Tools follow the TechLearn Academy plugins frame."""

from urllib.parse import quote

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from backend.db import execute, one, rows
from backend.pages.academy_content import PLUGINS
from backend.pages.common import shell, templates

router = APIRouter()


def _ensure_plugins() -> None:
    if one("SELECT id FROM plugins WHERE section = ?", ("academy",)):
        return
    for name, blurb, mark, installed in PLUGINS:
        execute(
            """
            INSERT INTO plugins (name, blurb, mark, mark_class, section, installed)
            VALUES (?, ?, ?, 'academy', 'academy', ?)
            """,
            (name, blurb, mark, installed),
        )


@router.get("/plugins")
def plugins_page(request: Request):
    _ensure_plugins()
    plugins = rows("SELECT * FROM plugins WHERE section = ? ORDER BY id", ("academy",))
    for item in plugins:
        if item["name"] == "Python Playground":
            item["href"] = "/lab"
        else:
            item["href"] = "/chat?q=" + quote(f"Help me use {item['name']}. {item['blurb']}")
    context = shell("plugins")
    context["plugins"] = plugins
    context["installed_count"] = sum(1 for item in plugins if item["installed"])
    return templates.TemplateResponse(request, "pages/plugins.html", context)


@router.post("/plugins/{plugin_id}/install")
def install_plugin(plugin_id: int):
    execute("UPDATE plugins SET installed = 1 WHERE id = ? AND section = 'academy'", (plugin_id,))
    return RedirectResponse("/plugins", status_code=303)
