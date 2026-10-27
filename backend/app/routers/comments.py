"""コメント投稿（FR-005）。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app import audit, models, schemas
from app.auth import Role, authenticate, requires_editor
from app.database import get_db
from app.domain.items import get_item_or_404

router = APIRouter()


@router.post(
    "",
    response_model=schemas.CommentOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[requires_editor],
)
def create_comment(
    payload: schemas.CommentCreate,
    db: Session = Depends(get_db),
    actor: Role = Depends(authenticate),
) -> models.Comment:
    get_item_or_404(db, payload.item_type, payload.item_id)
    comment = models.Comment(
        item_type=payload.item_type,
        item_id=payload.item_id,
        body=payload.body,
        tag=payload.tag,
    )
    db.add(comment)
    db.flush()
    audit.record(
        db, actor, "comment.create", payload.item_type, payload.item_id, {"comment_id": comment.id}
    )
    db.commit()
    db.refresh(comment)
    return comment
