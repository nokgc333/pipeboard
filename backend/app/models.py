"""SQLAlchemyモデル（仕様書§4.2参照）。"""

from __future__ import annotations

import datetime

from sqlalchemy import Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def _utc_now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


class _ItemColumns:
    """shots と assets が共有する列(同一スキーマ、別テーブル。ADR-0002)。"""

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(20), default="not_started")
    created_at: Mapped[datetime.datetime] = mapped_column(default=_utc_now)
    updated_at: Mapped[datetime.datetime] = mapped_column(default=_utc_now, onupdate=_utc_now)


class Shot(_ItemColumns, Base):
    __tablename__ = "shots"


class Asset(_ItemColumns, Base):
    __tablename__ = "assets"


class Version(Base):
    """item_type/item_idによるポリモーフィック関連。DBレベルのFK制約は張らない（ADR-0002）。"""

    __tablename__ = "versions"
    __table_args__ = (Index("idx_versions_item", "item_type", "item_id"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    item_type: Mapped[str] = mapped_column(String(10))
    item_id: Mapped[int] = mapped_column()
    version_number: Mapped[int] = mapped_column()
    thumbnail_path: Mapped[str] = mapped_column(String(255))
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(default=_utc_now)


class Comment(Base):
    __tablename__ = "comments"
    __table_args__ = (Index("idx_comments_item", "item_type", "item_id"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    item_type: Mapped[str] = mapped_column(String(10))
    item_id: Mapped[int] = mapped_column()
    body: Mapped[str] = mapped_column(Text())
    tag: Mapped[str | None] = mapped_column(String(30), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(default=_utc_now)


class AuditLog(Base):
    """誰が・いつ・何をしたか。変更系の操作が成功したときだけ、同じトランザクションで残す。"""

    __tablename__ = "audit_log"
    __table_args__ = (Index("idx_audit_item", "item_type", "item_id"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    actor: Mapped[str] = mapped_column(String(20))
    action: Mapped[str] = mapped_column(String(40))
    item_type: Mapped[str] = mapped_column(String(10))
    item_id: Mapped[int] = mapped_column()
    detail: Mapped[str | None] = mapped_column(Text(), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(default=_utc_now)
