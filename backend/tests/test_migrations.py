"""Alembic のマイグレーションのテスト(空の DB から最新まで再現でき、モデルと食い違わない)。"""

from __future__ import annotations

from pathlib import Path

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect

from app import models  # noqa: F401
from app.database import Base
from app.migrate import alembic_config, upgrade_to_head

TABLES = {"shots", "assets", "versions", "comments"}


def _url(tmp_path: Path) -> str:
    return f"sqlite:///{tmp_path / 'migrated.db'}"


def test_upgrading_an_empty_database_creates_every_table(tmp_path: Path) -> None:
    url = _url(tmp_path)

    upgrade_to_head(url)

    assert TABLES <= set(inspect(create_engine(url)).get_table_names())


def test_the_migrated_schema_matches_the_models(tmp_path: Path) -> None:
    url = _url(tmp_path)
    upgrade_to_head(url)

    with create_engine(url).connect() as connection:
        differences = compare_metadata(MigrationContext.configure(connection), Base.metadata)

    assert differences == []


def test_the_indexes_on_the_polymorphic_columns_exist(tmp_path: Path) -> None:
    url = _url(tmp_path)
    upgrade_to_head(url)

    inspector = inspect(create_engine(url))

    assert {i["name"] for i in inspector.get_indexes("versions")} == {"idx_versions_item"}
    assert {i["name"] for i in inspector.get_indexes("comments")} == {"idx_comments_item"}


def test_upgrading_twice_is_harmless(tmp_path: Path) -> None:
    url = _url(tmp_path)

    upgrade_to_head(url)
    upgrade_to_head(url)

    assert TABLES <= set(inspect(create_engine(url)).get_table_names())


def test_downgrading_to_base_removes_the_tables(tmp_path: Path) -> None:
    url = _url(tmp_path)
    upgrade_to_head(url)

    command.downgrade(alembic_config(url), "base")

    assert not (TABLES & set(inspect(create_engine(url)).get_table_names()))


def test_a_url_with_a_percent_sign_in_the_password_survives_the_config() -> None:
    url = "postgresql+psycopg://user:p%40ss@localhost/pipeboard"

    assert alembic_config(url).get_main_option("sqlalchemy.url") == url


def test_existing_shots_survive_the_hierarchy_migration_with_no_sequence(tmp_path: Path) -> None:
    from sqlalchemy import text

    url = _url(tmp_path)
    command.upgrade(alembic_config(url), "0003")
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO shots (name, status, created_at, updated_at) "
                "VALUES ('SHOT010', 'done', '2026-01-01', '2026-01-01')"
            )
        )

    command.upgrade(alembic_config(url), "head")

    with engine.connect() as connection:
        row = connection.execute(text("SELECT name, status, sequence_id FROM shots")).one()
    assert tuple(row) == ("SHOT010", "done", None)


def test_a_database_created_before_migrations_can_be_stamped_and_then_upgraded(
    tmp_path: Path,
) -> None:
    from sqlalchemy import text

    from app.migrate import stamp

    url = _url(tmp_path)
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE shots (id INTEGER PRIMARY KEY AUTOINCREMENT, name VARCHAR(100) "
                "NOT NULL, status VARCHAR(20) NOT NULL, created_at DATETIME NOT NULL, "
                "updated_at DATETIME NOT NULL)"
            )
        )
        connection.execute(
            text(
                "CREATE TABLE assets (id INTEGER PRIMARY KEY AUTOINCREMENT, name VARCHAR(100) "
                "NOT NULL, status VARCHAR(20) NOT NULL, created_at DATETIME NOT NULL, "
                "updated_at DATETIME NOT NULL)"
            )
        )
        connection.execute(
            text(
                "CREATE TABLE versions (id INTEGER PRIMARY KEY AUTOINCREMENT, item_type "
                "VARCHAR(10) NOT NULL, item_id INTEGER NOT NULL, version_number INTEGER NOT "
                "NULL, thumbnail_path VARCHAR(255) NOT NULL, original_filename VARCHAR(255), "
                "created_at DATETIME NOT NULL)"
            )
        )
        connection.execute(text("CREATE INDEX idx_versions_item ON versions (item_type, item_id)"))
        connection.execute(
            text(
                "CREATE TABLE comments (id INTEGER PRIMARY KEY AUTOINCREMENT, item_type "
                "VARCHAR(10) NOT NULL, item_id INTEGER NOT NULL, body TEXT NOT NULL, tag "
                "VARCHAR(30), created_at DATETIME NOT NULL)"
            )
        )
        connection.execute(text("CREATE INDEX idx_comments_item ON comments (item_type, item_id)"))
        connection.execute(
            text(
                "INSERT INTO shots (name, status, created_at, updated_at) "
                "VALUES ('SHOT010', 'done', '2026-01-01', '2026-01-01')"
            )
        )

    stamp("0001", url)
    upgrade_to_head(url)

    with engine.connect() as connection:
        names = [r[0] for r in connection.execute(text("SELECT name FROM shots"))]
    assert names == ["SHOT010"]
    assert {"audit_log", "check_results", "projects", "sequences"} <= set(
        inspect(engine).get_table_names()
    )


def test_the_migrate_command_line_is_checked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app import migrate

    monkeypatch.setattr(migrate, "DATABASE_URL", _url(tmp_path))
    monkeypatch.setattr(migrate, "upgrade_to_head", lambda *a, **k: None)
    monkeypatch.setattr(migrate, "stamp", lambda *a, **k: None)

    assert migrate.main(["m"]) == 0
    assert migrate.main(["m", "stamp", "0001"]) == 0
    assert migrate.main(["m", "bogus"]) == 2
