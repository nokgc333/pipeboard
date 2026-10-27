"""PostgreSQL での動作確認(PIPEBOARD_TEST_POSTGRES_URL が設定されているときだけ実行する)。

CI では PostgreSQL のサービスコンテナに接続する。ローカルでは、使い捨ての DB の URL を指定する。
"""

from __future__ import annotations

import os
from collections.abc import Generator

import pytest
from alembic import command
from fastapi.testclient import TestClient
from sqlalchemy import inspect
from sqlalchemy.orm import Session, sessionmaker

from app.database import build_engine, get_db
from app.main import app
from app.migrate import alembic_config

URL = os.environ.get("PIPEBOARD_TEST_POSTGRES_URL")

pytestmark = pytest.mark.skipif(URL is None, reason="PIPEBOARD_TEST_POSTGRES_URL is not set")


@pytest.fixture()
def pg_client() -> Generator[TestClient, None, None]:
    assert URL is not None
    config = alembic_config(URL)
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    engine = build_engine(URL)
    factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override() -> Generator[Session, None, None]:
        db = factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
    engine.dispose()


def test_the_migrations_create_every_table_on_postgresql() -> None:
    assert URL is not None
    command.downgrade(alembic_config(URL), "base")
    command.upgrade(alembic_config(URL), "head")

    tables = set(inspect(build_engine(URL)).get_table_names())

    assert {"shots", "assets", "versions", "comments", "audit_log"} <= tables


def test_creating_listing_searching_and_auditing_work_on_postgresql(
    pg_client: TestClient,
) -> None:
    for name in ("SHOT010", "SHOT020", "Chair"):
        assert pg_client.post("/shots", json={"name": name}).status_code == 201

    listed = pg_client.get("/shots?q=shot&limit=1")

    assert [s["name"] for s in listed.json()] == ["SHOT020"]
    assert listed.headers["X-Total-Count"] == "2"
    assert len(pg_client.get("/audit-log").json()) == 3


def test_deleting_an_item_removes_its_comments_on_postgresql(pg_client: TestClient) -> None:
    shot_id = pg_client.post("/shots", json={"name": "SHOT010"}).json()["id"]
    pg_client.post("/comments", json={"item_type": "shot", "item_id": shot_id, "body": "x"})

    assert pg_client.delete(f"/shots/{shot_id}").status_code == 204
    assert pg_client.get(f"/shots/{shot_id}").status_code == 404
