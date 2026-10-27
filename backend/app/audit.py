"""監査ログ(誰が・いつ・何を)の記録。変更と同じトランザクションで書き、コミット後に Webhook へ流す。"""

from __future__ import annotations

import datetime
import json
from typing import Any

from sqlalchemy import event
from sqlalchemy.orm import Session

from app import models, webhooks
from app.auth import Role

PENDING_KEY = "pipeboard_pending_events"


def record(
    db: Session,
    actor: Role,
    action: str,
    item_type: str,
    item_id: int,
    detail: dict[str, Any] | None = None,
) -> None:
    """監査ログを 1 件、現在のトランザクションに足す(コミットは呼び出し側)。"""
    now = datetime.datetime.now(datetime.timezone.utc)
    encoded = json.dumps(detail, ensure_ascii=False, sort_keys=True) if detail else None
    db.add(
        models.AuditLog(
            actor=actor.name.lower(),
            action=action,
            item_type=item_type,
            item_id=item_id,
            detail=encoded,
            created_at=now,
        )
    )
    db.info.setdefault(PENDING_KEY, []).append(
        {
            "action": action,
            "actor": actor.name.lower(),
            "item_type": item_type,
            "item_id": item_id,
            "detail": detail or {},
            "at": now.isoformat(),
        }
    )


@event.listens_for(Session, "after_commit")
def _publish_after_commit(session: Session) -> None:
    for pending in session.info.pop(PENDING_KEY, []):
        webhooks.notify(pending)


@event.listens_for(Session, "after_rollback")
def _discard_after_rollback(session: Session) -> None:
    session.info.pop(PENDING_KEY, None)
