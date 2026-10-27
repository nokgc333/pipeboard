"""コメントのスキーマ。"""

from __future__ import annotations

import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.items import ItemType


class CommentCreate(BaseModel):
    item_type: ItemType
    item_id: int
    body: str = Field(min_length=1, max_length=2000)
    tag: str | None = Field(default=None, max_length=30)


class CommentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    item_type: ItemType
    item_id: int
    body: str
    tag: str | None
    created_at: datetime.datetime
