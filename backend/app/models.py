"""SQLAlchemyモデル（仕様書§4.2参照）。"""

from __future__ import annotations

import datetime

from sqlalchemy import Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Shot(Base):
    __tablename__ = "shots"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(20), default="not_started")
    created_at: Mapped[datetime.datetime] = mapped_column(
        default=lambda: datetime.datetime.now(datetime.timezone.utc)
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        onupdate=lambda: datetime.datetime.now(datetime.timezone.utc),
    )


class Asset(Base):
    """shotsと同一スキーマだが別テーブルとして分離する（ADR-0002）。"""

    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(20), default="not_started")
    created_at: Mapped[datetime.datetime] = mapped_column(
        default=lambda: datetime.datetime.now(datetime.timezone.utc)
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        onupdate=lambda: datetime.datetime.now(datetime.timezone.utc),
    )


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
    created_at: Mapped[datetime.datetime] = mapped_column(
        default=lambda: datetime.datetime.now(datetime.timezone.utc)
    )


class Comment(Base):
    __tablename__ = "comments"
    __table_args__ = (Index("idx_comments_item", "item_type", "item_id"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    item_type: Mapped[str] = mapped_column(String(10))
    item_id: Mapped[int] = mapped_column()
    body: Mapped[str] = mapped_column(Text())
    tag: Mapped[str | None] = mapped_column(String(30), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        default=lambda: datetime.datetime.now(datetime.timezone.utc)
    )
