"""shots / assets のスキーマ。"""

from __future__ import annotations

import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ItemType = Literal["shot", "asset"]
ItemStatus = Literal["not_started", "in_progress", "in_review", "done"]


class ItemCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class ItemUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class ItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    status: ItemStatus
    created_at: datetime.datetime
    updated_at: datetime.datetime


class StatusUpdate(BaseModel):
    status: str
