"""SQLite を、複数の読み手と 1 つの書き手が同時に使える設定(WAL)にすることのテスト。"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import text

from app.database import build_engine, is_file_sqlite


def _pragma(engine, name: str):  # type: ignore[no-untyped-def]
    with engine.connect() as connection:
        return connection.execute(text(f"PRAGMA {name}")).scalar()


def test_a_file_database_uses_write_ahead_logging(tmp_path: Path) -> None:
    engine = build_engine(f"sqlite:///{tmp_path / 'wal.db'}")

    assert _pragma(engine, "journal_mode") == "wal"


def test_a_busy_timeout_is_set_so_a_second_writer_waits_instead_of_failing(
    tmp_path: Path,
) -> None:
    engine = build_engine(f"sqlite:///{tmp_path / 'busy.db'}")

    assert _pragma(engine, "busy_timeout") == 5000


def test_synchronous_is_normal_which_is_safe_with_wal(tmp_path: Path) -> None:
    engine = build_engine(f"sqlite:///{tmp_path / 'sync.db'}")

    assert _pragma(engine, "synchronous") == 1


def test_an_in_memory_database_is_left_alone() -> None:
    engine = build_engine("sqlite://")

    assert _pragma(engine, "journal_mode") == "memory"


def test_only_file_backed_sqlite_urls_are_detected() -> None:
    assert is_file_sqlite("sqlite:///./a.db")
    assert is_file_sqlite("sqlite:////abs/a.db")
    assert not is_file_sqlite("sqlite://")
    assert not is_file_sqlite("sqlite:///:memory:")
    assert not is_file_sqlite("postgresql+psycopg://u:p@h/db")
