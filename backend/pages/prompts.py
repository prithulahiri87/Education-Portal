"""Browse Prompts page. Cards follow the TechLearn Academy prompt frame."""

from urllib.parse import quote

from fastapi import APIRouter, Request

from backend.pages.academy_content import PROMPTS
from backend.pages.common import shell, templates

router = APIRouter()


@router.get("/prompts")
def prompts_page(request: Request):
    context = shell("prompts")
    cards = []
    for item in PROMPTS:
        cards.append({**item, "href": "/chat?q=" + quote(item["body"])})
    context["prompts"] = cards
    context["saved_count"] = sum(1 for item in cards if item["saved"])
    return templates.TemplateResponse(request, "pages/prompts.html", context)
