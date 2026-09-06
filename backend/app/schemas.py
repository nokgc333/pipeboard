"""Pydanticスキーマ（仕様書§4.2, §5.3参照）。"""

from __future__ import annotations

import datetime

from pydantic import BaseModel, ConfigDict, Field


class ItemCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class ItemUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class ItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    status: str
    created_at: datetime.datetime
    updated_at: datetime.datetime


class StatusUpdate(BaseModel):
    status: str


class VersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    item_type: str
    item_id: int
    version_number: int
    thumbnail_path: str
    original_filename: str | None
    created_at: datetime.datetime


class CommentCreate(BaseModel):
    item_type: str
    item_id: int
    body: str = Field(min_length=1, max_length=2000)
    tag: str | None = Field(default=None, max_length=30)


class CommentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    item_type: str
    item_id: int
    body: str
    tag: str | None
    created_at: datetime.datetime
