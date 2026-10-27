"""マイグレーションを最新まで適用する(起動時・seed・テストから使う)。"""

from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config

from app.database import DATABASE_URL

MIGRATIONS_DIR = Path(__file__).parent / "migrations"


def alembic_config(database_url: str) -> Config:
    config = Config()
    config.set_main_option("script_location", str(MIGRATIONS_DIR))
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    return config


def upgrade_to_head(database_url: str = DATABASE_URL) -> None:
    command.upgrade(alembic_config(database_url), "head")


if __name__ == "__main__":
    upgrade_to_head()
