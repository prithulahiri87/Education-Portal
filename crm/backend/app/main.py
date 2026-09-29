"""Harbor CRM API."""

import json
import logging
import secrets
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import get_engine, init_db, redact_database_url
from app.routes import router

logger = logging.getLogger("harbor")


def configure_logging():
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.handlers = [handler]
    logger.setLevel(logging.INFO)
    logger.propagate = False


@asynccontextmanager
async def lifespan(_app):
    configure_logging()
    init_db()
    settings = get_settings()
    logger.info(
        json.dumps(
            {
                "event": "startup",
                "database": get_engine().dialect.name,
                "database_target": redact_database_url(settings["database_url"]),
                "auth_required": bool(settings["api_token"]),
            }
        )
    )
    if settings["seed_on_start"]:
        from app.seed_data import seed

        seed()
    yield


app = FastAPI(title="Harbor CRM", version="0.1.0", lifespan=lifespan)
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings["cors_origins"],
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
    allow_credentials=False,
)


def require_token(request: Request):
    expected = get_settings()["api_token"]
    if not expected:
        return
    presented = request.headers.get("authorization", "")
    scheme, _, token = presented.partition(" ")
    if scheme.lower() != "bearer" or not token or not secrets.compare_digest(token, expected):
        raise HTTPException(status_code=401, detail="Authentication required")


@app.middleware("http")
async def shield(request: Request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    if request.url.path.startswith("/api"):
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
    logger.info(
        json.dumps(
            {
                "event": "request",
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
            }
        )
    )
    return response


@app.get("/")
def root():
    return {"service": "harbor-crm", "health": "/api/health", "docs": "/docs"}


@app.get("/api/health")
def health():
    current = get_settings()
    return {
        "status": "ok",
        "service": "harbor-crm",
        "database": get_engine().dialect.name,
        "auth_required": bool(current["api_token"]),
    }


app.include_router(router, dependencies=[Depends(require_token)])
