"""shots/assetsで共通のCRUDロジックをファクトリ化する（DRY、両ルータで重複させない）。

shotsとassetsは仕様書§4.2の通り同一スキーマだが別テーブルに分離されている（ADR-0002）。
振る舞い（一覧・作成・更新・ステータス変更・カスケード削除）は完全に共通なため、
モデルクラスとitem_type文字列を受け取るファクトリ関数として1箇所にまとめる。
"""

from __future__ import annotations

from typing import cast

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.auth import requires_admin, requires_editor, requires_viewer
from app.database import get_db
from app.domain.status_transition import is_valid_status

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
    def list_items(db: Session = Depends(get_db)) -> list[Item]:
        return cast(list[Item], db.query(model).order_by(model.created_at.desc()).all())

    @router.post(
        "",
        response_model=schemas.ItemOut,
        status_code=status.HTTP_201_CREATED,
        dependencies=[requires_editor],
    )
    def create_item(
        payload: schemas.ItemCreate, db: Session = Depends(get_db)
    ) -> models.Shot | models.Asset:
        item = model(name=payload.name)
        db.add(item)
        db.commit()
        db.refresh(item)
        return item

    @router.get("/{item_id}", response_model=schemas.ItemOut, dependencies=[requires_viewer])
    def get_item(item_id: int, db: Session = Depends(get_db)) -> models.Shot | models.Asset:
        return _get_or_404(item_id, db)

    @router.put("/{item_id}", response_model=schemas.ItemOut, dependencies=[requires_editor])
    def update_item(
        item_id: int, payload: schemas.ItemUpdate, db: Session = Depends(get_db)
    ) -> models.Shot | models.Asset:
        item = _get_or_404(item_id, db)
        item.name = payload.name
        db.commit()
        db.refresh(item)
        return item

    @router.patch(
        "/{item_id}/status", response_model=schemas.ItemOut, dependencies=[requires_editor]
    )
    def update_status(
        item_id: int, payload: schemas.StatusUpdate, db: Session = Depends(get_db)
    ) -> models.Shot | models.Asset:
        item = _get_or_404(item_id, db)
        if not is_valid_status(payload.status):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {payload.status}",
            )
        item.status = payload.status
        db.commit()
        db.refresh(item)
        return item

    @router.delete(
        "/{item_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[requires_admin]
    )
    def delete_item(item_id: int, db: Session = Depends(get_db)) -> None:
        item = _get_or_404(item_id, db)
        # DBレベルのFK制約がないため（ADR-0002）、アプリ層で明示的にカスケード削除する
        db.query(models.Version).filter_by(item_type=item_type, item_id=item_id).delete()
        db.query(models.Comment).filter_by(item_type=item_type, item_id=item_id).delete()
        db.delete(item)
        db.commit()

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
