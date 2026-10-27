"""database.py の接続設定・セッションと、seed.py のデモデータ投入のテスト。"""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app import models
from app.database import Base, connect_args_for, get_db
from app.seed import seed


def _session_factory(tmp_path: Path) -> tuple[Engine, sessionmaker[Session]]:
    engine = create_engine(f"sqlite:///{tmp_path / 'seed.db'}")
    return engine, sessionmaker(autocommit=False, autoflush=False, bind=engine)


class TestConnectArgs:
    def test_sqlite_allows_use_from_other_threads(self) -> None:
        assert connect_args_for("sqlite:///./a.db") == {"check_same_thread": False}

    def test_sqlite_in_memory_allows_use_from_other_threads(self) -> None:
        assert connect_args_for("sqlite://") == {"check_same_thread": False}

    def test_other_databases_get_no_extra_arguments(self) -> None:
        assert connect_args_for("postgresql+psycopg://u:p@h/db") == {}


class TestGetDb:
    def test_yields_a_session_and_closes_it_afterwards(self) -> None:
        generator = get_db()
        session = next(generator)

        assert session.is_active
        generator.close()
        assert session.get_bind() is not None

    def test_closes_the_session_even_when_the_caller_raises(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        closed: list[bool] = []
        original_close = Session.close

        def recording_close(self: Session) -> None:
            closed.append(True)
            original_close(self)

        monkeypatch.setattr(Session, "close", recording_close)
        generator = get_db()
        next(generator)

        with pytest.raises(RuntimeError):
            generator.throw(RuntimeError("boom"))

        assert closed == [True]


class TestSeed:
    def test_creates_the_demo_shots_and_assets_in_an_empty_database(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        engine, factory = _session_factory(tmp_path)

        seed(engine=engine, session_factory=factory)

        with factory() as db:
            assert db.query(models.Shot).count() == 4
            assert db.query(models.Asset).count() == 2
        assert "Seeded 4 shots and 2 assets." in capsys.readouterr().out

    def test_covers_every_status_of_the_board(self, tmp_path: Path) -> None:
        engine, factory = _session_factory(tmp_path)

        seed(engine=engine, session_factory=factory)

        with factory() as db:
            statuses = {s.status for s in db.query(models.Shot)}
        assert statuses == {"not_started", "in_progress", "in_review", "done"}

    def test_running_twice_does_not_add_duplicates(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        engine, factory = _session_factory(tmp_path)
        seed(engine=engine, session_factory=factory)
        capsys.readouterr()

        seed(engine=engine, session_factory=factory)

        with factory() as db:
            assert db.query(models.Shot).count() == 4
        assert "Already seeded" in capsys.readouterr().out

    def test_tables_exist_after_seeding(self, tmp_path: Path) -> None:
        engine, factory = _session_factory(tmp_path)

        seed(engine=engine, session_factory=factory)

        assert {"shots", "assets"} <= set(Base.metadata.tables)
