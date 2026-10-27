"""プロジェクト / シーケンスのスキーマ。"""

from __future__ import annotations

import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    created_at: datetime.datetime


class SequenceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class SequenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    name: str
    created_at: datetime.datetime


class SequenceAssign(BaseModel):
    sequence_id: int | None
