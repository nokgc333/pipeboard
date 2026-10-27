"""DB接続・セッション管理（仕様書§3参照）。"""

from __future__ import annotations

import os
from collections.abc import Generator

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

DATABASE_URL = os.environ.get("PIPEBOARD_DATABASE_URL", "sqlite:///./pipeboard.db")


def connect_args_for(url: str) -> dict[str, bool]:
    """SQLite は、FastAPI のスレッドプールから使うため、別スレッドでの利用を許す。"""
    return {"check_same_thread": False} if url.startswith("sqlite") else {}


def is_file_sqlite(url: str) -> bool:
    return url.startswith("sqlite") and url not in {"sqlite://", "sqlite:///:memory:"}


SQLITE_BUSY_TIMEOUT_MS = 5000


def build_engine(url: str) -> Engine:
    """接続を作る。ファイルの SQLite は WAL にして、読み取りが書き込みを待たないようにする。"""
    created = create_engine(url, connect_args=connect_args_for(url))
    if is_file_sqlite(url):

        @event.listens_for(created, "connect")
        def _configure(dbapi_connection, _record):  # type: ignore[no-untyped-def]
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute(f"PRAGMA busy_timeout={SQLITE_BUSY_TIMEOUT_MS}")
            cursor.close()

    return created


engine = build_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
