"""/healthz(生存確認)と /health(データベースまで含めた準備完了の確認)のテスト。"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database import get_db
from app.main import app


def test_healthz_only_says_the_process_is_alive(client: TestClient) -> None:
    assert client.get("/healthz").json() == {"status": "ok"}


def test_health_reports_the_database_and_the_version(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok", "version": app.version}


def test_health_is_503_when_the_database_cannot_be_queried(client: TestClient) -> None:
    class BrokenSession:
        def execute(self, *_: object, **__: object) -> None:
            raise RuntimeError("database is down")

        def close(self) -> None:
            return None

    def broken() -> Session:
        return BrokenSession()  # type: ignore[return-value]

    app.dependency_overrides[get_db] = broken

    response = client.get("/health")

    assert response.status_code == 503
    assert response.json()["title"] == "Database unavailable"


@pytest.fixture()
def token_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PIPEBOARD_AUTH_MODE", "token")
    monkeypatch.setenv("PIPEBOARD_API_TOKENS", "admin=admin-token-0003")


@pytest.mark.usefixtures("token_mode")
def test_health_stays_public_so_orchestrators_can_probe_it(client: TestClient) -> None:
    assert client.get("/health").status_code == 200
