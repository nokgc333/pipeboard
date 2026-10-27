"""監査ログの閲覧(管理者のみ)。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app import models, schemas
from app.auth import requires_admin
from app.database import get_db

router = APIRouter()


@router.get("", response_model=list[schemas.AuditLogOut], dependencies=[requires_admin])
def list_audit_log(
    response: Response,
    item_type: str | None = Query(default=None, max_length=10),
    item_id: int | None = Query(default=None, ge=1),
    action: str | None = Query(default=None, max_length=40),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[models.AuditLog]:
    query = db.query(models.AuditLog)
    if item_type:
        query = query.filter(models.AuditLog.item_type == item_type)
    if item_id:
        query = query.filter(models.AuditLog.item_id == item_id)
    if action:
        query = query.filter(models.AuditLog.action == action)
    response.headers["X-Total-Count"] = str(query.count())
    return query.order_by(models.AuditLog.id.desc()).offset(offset).limit(limit).all()
