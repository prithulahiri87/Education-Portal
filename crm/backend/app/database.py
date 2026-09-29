"""Database engine. SQLite is the local default; Postgres is selected with DATABASE_URL."""

import re
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import get_settings

_engine = None
_session_factory = None


class Base(DeclarativeBase):
    pass


def redact_database_url(url):
    return re.sub(r"://([^:/@]+):([^@]+)@", r"://\1:***@", url)


def _sqlite_path(url):
    if not url.startswith("sqlite"):
        return None
    if url in ("sqlite://", "sqlite:///:memory:"):
        return None
    raw = url[len("sqlite:///") :]
    return Path(raw)


def get_engine():
    global _engine
    if _engine is not None:
        return _engine
    url = get_settings()["database_url"]
    sqlite_path = _sqlite_path(url)
    if sqlite_path is not None:
        sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    kwargs = {}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
        if url in ("sqlite://", "sqlite:///:memory:"):
            kwargs["poolclass"] = StaticPool
    engine = create_engine(url, **kwargs)

    @event.listens_for(engine, "connect")
    def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record):
        if engine.dialect.name == "sqlite":
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    _engine = engine
    return engine


def get_session_factory():
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(bind=get_engine(), expire_on_commit=False)
    return _session_factory


def get_db():
    db = get_session_factory()()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from app import models  # noqa: F401

    Base.metadata.create_all(get_engine())
