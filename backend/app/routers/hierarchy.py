"""プロジェクト > シーケンス > ショット の階層。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
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

projects_router = APIRouter()
sequences_router = APIRouter()


def _project_or_404(db: Session, project_id: int) -> models.Project:
    project = db.get(models.Project, project_id)
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Project {project_id} not found")
    return project


def _conflict(message: str) -> HTTPException:
    return HTTPException(status.HTTP_409_CONFLICT, message)


@projects_router.get("", response_model=list[schemas.ProjectOut], dependencies=[requires_viewer])
def list_projects(db: Session = Depends(get_db)) -> list[models.Project]:
    return list(db.scalars(select(models.Project).order_by(models.Project.id.desc())))


@projects_router.post(
    "",
    response_model=schemas.ProjectOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[requires_editor],
)
def create_project(
    payload: schemas.ProjectCreate,
    db: Session = Depends(get_db),
    actor: Role = Depends(authenticate),
) -> models.Project:
    project = models.Project(name=payload.name)
    db.add(project)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise _conflict(f"Project '{payload.name}' already exists") from exc
    audit.record(db, actor, "project.create", "project", project.id, {"name": project.name})
    db.commit()
    db.refresh(project)
    return project


@projects_router.delete(
    "/{project_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[requires_admin]
)
def delete_project(
    project_id: int, db: Session = Depends(get_db), actor: Role = Depends(authenticate)
) -> None:
    project = _project_or_404(db, project_id)
    has_sequences = db.scalar(
        select(models.Sequence.id).where(models.Sequence.project_id == project_id).limit(1)
    )
    if has_sequences is not None:
        raise _conflict("Project still has sequences")
    audit.record(db, actor, "project.delete", "project", project_id, {"name": project.name})
    db.delete(project)
    db.commit()


@projects_router.get(
    "/{project_id}/sequences",
    response_model=list[schemas.SequenceOut],
    dependencies=[requires_viewer],
)
def list_sequences(project_id: int, db: Session = Depends(get_db)) -> list[models.Sequence]:
    _project_or_404(db, project_id)
    return list(
        db.scalars(
            select(models.Sequence)
            .where(models.Sequence.project_id == project_id)
            .order_by(models.Sequence.id.desc())
        )
    )


@projects_router.post(
    "/{project_id}/sequences",
    response_model=schemas.SequenceOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[requires_editor],
)
def create_sequence(
    project_id: int,
    payload: schemas.SequenceCreate,
    db: Session = Depends(get_db),
    actor: Role = Depends(authenticate),
) -> models.Sequence:
    _project_or_404(db, project_id)
    sequence = models.Sequence(project_id=project_id, name=payload.name)
    db.add(sequence)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise _conflict(f"Sequence '{payload.name}' already exists in this project") from exc
    audit.record(
        db,
        actor,
        "sequence.create",
        "sequence",
        sequence.id,
        {"name": sequence.name, "project_id": project_id},
    )
    db.commit()
    db.refresh(sequence)
    return sequence


@sequences_router.delete(
    "/{sequence_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[requires_admin]
)
def delete_sequence(
    sequence_id: int, db: Session = Depends(get_db), actor: Role = Depends(authenticate)
) -> None:
    sequence = db.get(models.Sequence, sequence_id)
    if sequence is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Sequence {sequence_id} not found")
    has_shots = db.scalar(
        select(models.Shot.id).where(models.Shot.sequence_id == sequence_id).limit(1)
    )
    if has_shots is not None:
        raise _conflict("Sequence still has shots")
    audit.record(db, actor, "sequence.delete", "sequence", sequence_id, {"name": sequence.name})
    db.delete(sequence)
    db.commit()
