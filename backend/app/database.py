"""DB接続・セッション管理（仕様書§3参照）。"""

from __future__ import annotations

import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

DATABASE_URL = os.environ.get("PIPEBOARD_DATABASE_URL", "sqlite:///./pipeboard.db")


def connect_args_for(url: str) -> dict[str, bool]:
    """SQLite は、FastAPI のスレッドプールから使うため、別スレッドでの利用を許す。"""
    return {"check_same_thread": False} if url.startswith("sqlite") else {}


engine = create_engine(DATABASE_URL, connect_args=connect_args_for(DATABASE_URL))
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
