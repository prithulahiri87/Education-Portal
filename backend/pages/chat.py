"""New Chat page."""

from fastapi import APIRouter, Request

from backend.pages.common import shell, templates

router = APIRouter()


@router.get("/chat")
def chat_page(request: Request):
    return templates.TemplateResponse(request, "pages/chat.html", shell("chat"))
