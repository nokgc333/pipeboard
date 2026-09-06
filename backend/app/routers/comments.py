"""コメント投稿（FR-005）。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db

router = APIRouter()


@router.post("", response_model=schemas.CommentOut, status_code=status.HTTP_201_CREATED)
def create_comment(payload: schemas.CommentCreate, db: Session = Depends(get_db)) -> models.Comment:
    comment = models.Comment(
        item_type=payload.item_type,
        item_id=payload.item_id,
        body=payload.body,
        tag=payload.tag,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment
