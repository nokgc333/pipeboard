"""pytest共通フィクスチャ。テストごとに独立したin-memory SQLiteを使う。"""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app import rate_limit
from app.database import Base, get_db
from app.main import app


@pytest.fixture(autouse=True)
def isolated_upload_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """テストが実プロジェクトのuploads/を汚さないよう、一時ディレクトリに差し替える。"""
    monkeypatch.setenv("PIPEBOARD_UPLOAD_DIR", str(tmp_path / "uploads"))


@pytest.fixture(autouse=True)
def fresh_rate_limiter() -> None:
    rate_limit.reset()


@pytest.fixture()
def db_session_factory() -> Generator[sessionmaker[Session], None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture()
def client(
    db_session_factory: sessionmaker[Session],
) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        db = db_session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
