"""Retrieve context from Chroma and call an OpenAI-compatible chat API."""

from __future__ import annotations

import httpx

from backend.config import get_settings
from backend.store import store


class MissingApiKeyError(Exception):
    """Raised when OPENAI_API_KEY is not configured."""


def build_messages(question: str, history: list[dict], sources: list[dict]) -> list[dict]:
    if sources:
        blocks = []
        for index, item in enumerate(sources, start=1):
            blocks.append(f"[{index}] source: {item['source']}\n{item['text']}")
        context = "\n\n".join(blocks)
    else:
        context = "No documents were retrieved from the vector database."

    system = (
        "You are a helpful assistant. Answer the user using the retrieved context. "
        "If the context does not contain the answer, say you do not know based on the documents. "
        "Mention the source name when you use a passage.\n\n"
        f"Retrieved context:\n{context}"
    )
    messages = [{"role": "system", "content": system}]
    for item in history:
        role = item.get("role")
        content = (item.get("content") or "").strip()
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": question})
    return messages


def latest_user_question(messages: list[dict]) -> tuple[str | None, list[dict]]:
    """Split an OpenAI-style message list into the latest user turn and prior turns."""
    history: list[dict] = []
    question = None
    for message in messages:
        role = message.get("role")
        content = message.get("content") or ""
        if isinstance(content, list):
            content = " ".join(
                part.get("text", "")
                for part in content
                if isinstance(part, dict) and part.get("type", "text") == "text"
            )
        content = str(content).strip()
        if role == "user":
            if question is not None:
                history.append({"role": "user", "content": question})
            question = content
        elif role == "assistant" and content:
            history.append({"role": "assistant", "content": content})
    return question, history


async def answer_question(question: str, history: list[dict] | None = None) -> dict:
    sources = store.query(question)
    messages = build_messages(question, history or [], sources)
    reply = await complete(messages)
    return {"answer": reply, "sources": sources}


async def complete(messages: list[dict]) -> str:
    settings = get_settings()
    if not settings["api_key"]:
        raise MissingApiKeyError(
            "OPENAI_API_KEY is not set. Add it to the project .env file and restart the API."
        )

    url = f"{settings['base_url']}/chat/completions"
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                url,
                headers={
                    "Authorization": f"Bearer {settings['api_key']}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings["model"],
                    "messages": messages,
                    "temperature": 0.2,
                },
            )
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        message = "The language model API returned an error."
        try:
            body = exc.response.json()
            message = body.get("error", {}).get("message", message)
        except Exception:
            text = exc.response.text.strip()
            if text:
                message = text[:300]
        raise RuntimeError(message) from exc
    except httpx.HTTPError as exc:
        raise RuntimeError("Could not reach the language model API.") from exc

    data = response.json()
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError("The language model API returned an unexpected response.") from exc
