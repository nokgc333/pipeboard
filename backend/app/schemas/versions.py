"""バージョン画像のスキーマ。"""

from __future__ import annotations

import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.items import ItemType


class VersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    item_type: ItemType
    item_id: int
    version_number: int
    thumbnail_path: str
    original_filename: str | None
    created_at: datetime.datetime
