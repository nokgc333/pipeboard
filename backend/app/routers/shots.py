"""ショット用ルータ（実体はdomain.items.create_item_routerを利用、DRY）。"""

from __future__ import annotations

from app import models
from app.domain.items import create_item_router

router = create_item_router(models.Shot, "shot")
