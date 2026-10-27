"""shots/assetsで共通のCRUDロジックをファクトリ化する（DRY、両ルータで重複させない）。

shotsとassetsは仕様書§4.2の通り同一スキーマだが別テーブルに分離されている（ADR-0002）。
振る舞い（一覧・作成・更新・ステータス変更・カスケード削除）は完全に共通なため、
モデルクラスとitem_type文字列を受け取るファクトリ関数として1箇所にまとめる。
"""

from __future__ import annotations

from typing import cast

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app import audit, models, schemas
from app.auth import (
    Role,
    authenticate,
    requires_admin,
    requires_editor,
    requires_viewer,
)
from app.database import get_db
from app.domain.publish_gate import CheckSummary, evaluate_gate
from app.domain.status_transition import is_valid_status
from app.gate_settings import load_required_checks

DEFAULT_PAGE_SIZE = 500
MAX_PAGE_SIZE = 500
ItemModel = type[models.Shot] | type[models.Asset]
Item = models.Shot | models.Asset


ITEM_MODELS: dict[str, ItemModel] = {"shot": models.Shot, "asset": models.Asset}


def get_item_or_404(db: Session, item_type: str, item_id: int) -> Item:
    """item_type の表に item_id の行があれば返し、なければ 404 にする。

    versions / comments は item_type + item_id で対象を指す(DB の外部キーは張らない、ADR-0002)ため、
    存在の確認はアプリ層で行う。
    """
    item = db.get(ITEM_MODELS[item_type], item_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{item_type.capitalize()} {item_id} not found",
        )
    return cast(Item, item)


def create_item_router(model: ItemModel, item_type: str) -> APIRouter:
    router = APIRouter()

    def _get_or_404(item_id: int, db: Session) -> Item:
        return get_item_or_404(db, item_type, item_id)

    @router.get("", response_model=list[schemas.ItemOut], dependencies=[requires_viewer])
    def list_items(
        response: Response,
        q: str | None = Query(default=None, max_length=100),
        status_filter: schemas.ItemStatus | None = Query(default=None, alias="status"),
        limit: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
        offset: int = Query(default=0, ge=0),
        db: Session = Depends(get_db),
    ) -> list[Item]:
        query = db.query(model)
        if q:
            query = query.filter(model.name.icontains(q, autoescape=True))
        if status_filter:
            query = query.filter(model.status == status_filter)
        response.headers["X-Total-Count"] = str(query.count())
        return cast(
            list[Item],
            query.order_by(model.created_at.desc(), model.id.desc())
            .offset(offset)
            .limit(limit)
            .all(),
        )

    @router.post(
        "",
        response_model=schemas.ItemOut,
        status_code=status.HTTP_201_CREATED,
        dependencies=[requires_editor],
    )
    def create_item(
        payload: schemas.ItemCreate,
        db: Session = Depends(get_db),
        actor: Role = Depends(authenticate),
    ) -> models.Shot | models.Asset:
        item = model(name=payload.name)
        db.add(item)
        db.flush()
        audit.record(db, actor, f"{item_type}.create", item_type, item.id, {"name": item.name})
        db.commit()
        db.refresh(item)
        return item

    def _latest_checks(db: Session, item_id: int) -> dict[str, CheckSummary]:
        latest: dict[str, CheckSummary] = {}
        rows = (
            db.query(models.CheckResult)
            .filter_by(item_type=item_type, item_id=item_id)
            .order_by(models.CheckResult.id.desc())
            .all()
        )
        for row in rows:
            latest.setdefault(row.tool, CheckSummary(tool=row.tool, passed=row.passed))
        return latest

    @router.get("/{item_id}", response_model=schemas.ItemOut, dependencies=[requires_viewer])
    def get_item(item_id: int, db: Session = Depends(get_db)) -> models.Shot | models.Asset:
        return _get_or_404(item_id, db)

    @router.put("/{item_id}", response_model=schemas.ItemOut, dependencies=[requires_editor])
    def update_item(
        item_id: int,
        payload: schemas.ItemUpdate,
        db: Session = Depends(get_db),
        actor: Role = Depends(authenticate),
    ) -> models.Shot | models.Asset:
        item = _get_or_404(item_id, db)
        audit.record(
            db,
            actor,
            f"{item_type}.rename",
            item_type,
            item_id,
            {"from": item.name, "to": payload.name},
        )
        item.name = payload.name
        db.commit()
        db.refresh(item)
        return item

    @router.patch(
        "/{item_id}/status", response_model=schemas.ItemOut, dependencies=[requires_editor]
    )
    def update_status(
        item_id: int,
        payload: schemas.StatusUpdate,
        db: Session = Depends(get_db),
        actor: Role = Depends(authenticate),
    ) -> models.Shot | models.Asset:
        item = _get_or_404(item_id, db)
        if not is_valid_status(payload.status):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {payload.status}",
            )
        decision = evaluate_gate(
            payload.status, load_required_checks(), _latest_checks(db, item_id)
        )
        if not decision.allowed:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(decision.reason))
        audit.record(
            db,
            actor,
            f"{item_type}.status",
            item_type,
            item_id,
            {"from": item.status, "to": payload.status},
        )
        item.status = payload.status
        db.commit()
        db.refresh(item)
        return item

    @router.delete(
        "/{item_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[requires_admin]
    )
    def delete_item(
        item_id: int, db: Session = Depends(get_db), actor: Role = Depends(authenticate)
    ) -> None:
        item = _get_or_404(item_id, db)
        audit.record(db, actor, f"{item_type}.delete", item_type, item_id, {"name": item.name})
        # DBレベルのFK制約がないため（ADR-0002）、アプリ層で明示的にカスケード削除する
        db.query(models.Version).filter_by(item_type=item_type, item_id=item_id).delete()
        db.query(models.Comment).filter_by(item_type=item_type, item_id=item_id).delete()
        db.query(models.CheckResult).filter_by(item_type=item_type, item_id=item_id).delete()
        db.delete(item)
        db.commit()

    @router.post(
        "/{item_id}/checks",
        response_model=schemas.CheckOut,
        status_code=status.HTTP_201_CREATED,
        dependencies=[requires_editor],
    )
    def submit_check(
        item_id: int,
        payload: schemas.CheckReportIn,
        db: Session = Depends(get_db),
        actor: Role = Depends(authenticate),
    ) -> models.CheckResult:
        _get_or_404(item_id, db)
        result = models.CheckResult(
            item_type=item_type,
            item_id=item_id,
            tool=payload.tool,
            subject=payload.subject,
            passed=not payload.has_errors,
            error_count=sum(f.severity == "error" for f in payload.findings),
            warning_count=sum(f.severity == "warning" for f in payload.findings),
            report=payload.model_dump_json(),
        )
        db.add(result)
        db.flush()
        audit.record(
            db,
            actor,
            f"{item_type}.check",
            item_type,
            item_id,
            {"tool": payload.tool, "passed": result.passed, "check_id": result.id},
        )
        db.commit()
        db.refresh(result)
        return result

    @router.get(
        "/{item_id}/checks",
        response_model=list[schemas.CheckOut],
        dependencies=[requires_viewer],
    )
    def list_checks(item_id: int, db: Session = Depends(get_db)) -> list[models.CheckResult]:
        _get_or_404(item_id, db)
        return (
            db.query(models.CheckResult)
            .filter_by(item_type=item_type, item_id=item_id)
            .order_by(models.CheckResult.id.desc())
            .all()
        )

    @router.get(
        "/{item_id}/versions",
        response_model=list[schemas.VersionOut],
        dependencies=[requires_viewer],
    )
    def list_versions(item_id: int, db: Session = Depends(get_db)) -> list[models.Version]:
        _get_or_404(item_id, db)
        return (
            db.query(models.Version)
            .filter_by(item_type=item_type, item_id=item_id)
            .order_by(models.Version.version_number.desc())
            .all()
        )

    @router.get(
        "/{item_id}/comments",
        response_model=list[schemas.CommentOut],
        dependencies=[requires_viewer],
    )
    def list_comments(item_id: int, db: Session = Depends(get_db)) -> list[models.Comment]:
        _get_or_404(item_id, db)
        return (
            db.query(models.Comment)
            .filter_by(item_type=item_type, item_id=item_id)
            .order_by(models.Comment.created_at.asc())
            .all()
        )

    return router
