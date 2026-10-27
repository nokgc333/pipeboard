"""デモデータ投入スクリプト。`python app/seed.py`で実行する。"""

from __future__ import annotations

from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from app import models
from app.database import Base, SessionLocal
from app.database import engine as default_engine


def seed(
    engine: Engine = default_engine,
    session_factory: sessionmaker[Session] = SessionLocal,
) -> None:
    Base.metadata.create_all(bind=engine)
    db = session_factory()
    try:
        if db.query(models.Shot).count() > 0:
            print("Already seeded, skipping.")
            return

        shots = [
            models.Shot(name="SHOT010", status="not_started"),
            models.Shot(name="SHOT020", status="in_progress"),
            models.Shot(name="SHOT030", status="in_review"),
            models.Shot(name="SHOT040", status="done"),
        ]
        assets = [
            models.Asset(name="Character_Hero", status="in_progress"),
            models.Asset(name="Prop_Chair", status="done"),
        ]
        db.add_all([*shots, *assets])
        db.commit()
        print(f"Seeded {len(shots)} shots and {len(assets)} assets.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
