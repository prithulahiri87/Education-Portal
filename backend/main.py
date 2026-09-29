"""FastAPI app: document ingest, RAG chat, and an OpenAI-style completions route."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Optional, Union

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend.config import get_settings
from backend.rag import MissingApiKeyError, answer_question, latest_user_question
from backend.store import store

HTML_DIR = Path(__file__).resolve().parent.parent / "ui-html"
HTML_PATH = HTML_DIR / "index.html"
ASSETS_DIR = HTML_DIR / "assets"
MAX_TEXT_CHARS = 1_000_000

app = FastAPI(title="RAG Chatbot", version="0.1.0")
if ASSETS_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="ui-assets")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8501",
        "http://127.0.0.1:8501",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


class HistoryItem(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[HistoryItem] = Field(default_factory=list)


class CompletionMessage(BaseModel):
    role: str
    content: Optional[Union[str, list]] = None


class CompletionsRequest(BaseModel):
    model: Optional[str] = None
    messages: list[CompletionMessage]


def _llm_http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, MissingApiKeyError):
        return HTTPException(status_code=503, detail=str(exc))
    return HTTPException(status_code=502, detail=str(exc))


@app.get("/")
def home():
    return FileResponse(HTML_PATH)


@app.get("/api/health")
def health():
    settings = get_settings()
    return {
        "status": "ok",
        "llm_configured": bool(settings["api_key"]),
        "model": settings["model"],
        "documents": store.count(),
    }


@app.post("/api/ingest")
async def ingest(request: Request):
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        body = await request.json()
        text = str(body.get("text") or "")
        source = str(body.get("source") or "pasted-text").strip() or "pasted-text"
    else:
        form = await request.form()
        upload = form.get("file")
        text_field = form.get("text")
        source_field = form.get("source")
        if upload is not None and getattr(upload, "filename", None):
            raw = await upload.read()
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise HTTPException(status_code=400, detail="Upload a UTF-8 text file.") from exc
            source = Path(str(source_field or upload.filename)).name or "upload.txt"
        else:
            text = str(text_field or "")
            source = str(source_field or "pasted-text").strip() or "pasted-text"

    text = text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Provide text or a UTF-8 file to ingest.")
    if len(text) > MAX_TEXT_CHARS:
        raise HTTPException(
            status_code=413,
            detail="Text is too large for this draft (max 1,000,000 characters).",
        )
    chunks = store.ingest(text, source)
    return {"source": source, "chunks": chunks}


@app.post("/api/chat")
async def chat(body: ChatRequest):
    question = body.message.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Message is empty.")
    history = [item.model_dump() for item in body.history]
    try:
        return await answer_question(question, history)
    except (MissingApiKeyError, RuntimeError) as exc:
        raise _llm_http_error(exc) from exc


@app.post("/v1/chat/completions")
async def chat_completions(body: CompletionsRequest):
    messages = [item.model_dump() for item in body.messages]
    question, history = latest_user_question(messages)
    if not question:
        raise HTTPException(status_code=400, detail="messages must include a user message.")
    try:
        result = await answer_question(question, history)
    except (MissingApiKeyError, RuntimeError) as exc:
        raise _llm_http_error(exc) from exc

    settings = get_settings()
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
        "object": "chat.completion",
        "model": settings["model"],
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": result["answer"]},
                "finish_reason": "stop",
            }
        ],
        "sources": result["sources"],
    }
