# RAG chatbot (first draft)

A small retrieval-augmented chatbot. The Python API embeds each question, searches a local Chroma vector database, and sends the matching passages plus chat history to an OpenAI-compatible chat API. HTML, React, and Streamlit screens all call that API.

## Layout

- `backend/` — FastAPI app, Chroma store, and seed data
- `ui-html/index.html` — browser UI served at `/`
- `ui-react/` — Vite + React UI
- `ui-python/app.py` — Streamlit UI

## Setup

```bash
cd rag-chatbot
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
cp .env.example .env
```

Edit `.env` and set `OPENAI_API_KEY`. Do not put the key in source files.

`OPENAI_BASE_URL` defaults to `https://api.openai.com/v1`. The API calls `{OPENAI_BASE_URL}/chat/completions`, so the base URL should already include `/v1`. Point `OPENAI_BASE_URL` at any OpenAI-compatible server (OpenAI, Groq, Ollama, and similar). `OPENAI_MODEL` defaults to `gpt-4o-mini`.

## Run

From the project root, with the virtualenv active:

```bash
python backend/seed.py
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

- HTML UI: http://127.0.0.1:8000
- React UI: `cd ui-react && npm install && npm run dev`, then open the printed local URL
- Python UI: `streamlit run ui-python/app.py`

## API

- `GET /api/health` — process status, whether a key is configured, and document count
- `POST /api/ingest` — JSON `{"text": "...", "source": "notes"}` or a multipart form with `file` (UTF-8 text) and optional `source`
- `POST /api/chat` — JSON `{"message": "...", "history": [{"role": "user", "content": "..."}]}` returns `answer` and `sources`
- `POST /v1/chat/completions` — OpenAI-style `messages` body. Retrieval runs on the latest user message. The response follows the chat-completion shape and adds a `sources` array.

If `OPENAI_API_KEY` is missing, chat routes return HTTP 503 with an explicit message. They do not invent an answer.

## Harbor CRM

`crm/` is a separate sales desk for Lead, Account, Contact, Opportunity, Quote, and QuoteLineItem. Setup and the architecture diagram are in [crm/README.md](crm/README.md).
