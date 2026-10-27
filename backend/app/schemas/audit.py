"""監査ログのスキーマ。"""

from __future__ import annotations

import datetime

from pydantic import BaseModel, ConfigDict


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    actor: str
    action: str
    item_type: str
    item_id: int
    detail: str | None
    created_at: datetime.datetime
