"""バージョン画像アップロード（FR-003, SEC-001/SEC-002）。"""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.auth import requires_editor
from app.database import get_db
from app.domain.filenames import generate_safe_filename
from app.domain.items import get_item_or_404

router = APIRouter()

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
CHUNK_SIZE = 1024 * 1024
MAX_ORIGINAL_FILENAME_LENGTH = 255
IMAGE_SIGNATURES: dict[str, tuple[bytes, ...]] = {
    ".png": (b"\x89PNG\r\n\x1a\n",),
    ".jpg": (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
    ".webp": (b"RIFF",),
}


def _matches_signature(ext: str, contents: bytes) -> bool:
    if not contents.startswith(IMAGE_SIGNATURES[ext]):
        return False
    if ext == ".webp":
        return contents[8:12] == b"WEBP"
    return True


def _upload_dir() -> Path:
    """アップロード先ディレクトリ。テストではPIPEBOARD_UPLOAD_DIRで一時ディレクトリに差し替える。"""
    return Path(os.environ.get("PIPEBOARD_UPLOAD_DIR", "uploads"))


@router.post(
    "",
    response_model=schemas.VersionOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[requires_editor],
)
async def upload_version(
    item_type: schemas.ItemType,
    item_id: int,
    file: UploadFile,
    db: Session = Depends(get_db),
) -> models.Version:
    get_item_or_404(db, item_type, item_id)
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS or file.content_type not in ALLOWED_MIME_TYPES:
        # SEC-001: 拡張子と実MIME typeの両方を検証（なりすまし拡張子対策）
        raise HTTPException(status_code=400, detail="Unsupported file type")

    buffer = bytearray()
    while chunk := await file.read(CHUNK_SIZE):
        buffer.extend(chunk)
        if len(buffer) > MAX_FILE_SIZE:
            raise HTTPException(status_code=413, detail="File too large (max 10MB)")
    contents = bytes(buffer)
    if not _matches_signature(ext, contents):
        raise HTTPException(status_code=400, detail="File content does not match its type")

    saved_name = generate_safe_filename(file.filename or "", ext)
    upload_dir = _upload_dir()
    upload_dir.mkdir(parents=True, exist_ok=True)
    (upload_dir / saved_name).write_bytes(contents)

    next_version = (
        db.query(models.Version).filter_by(item_type=item_type, item_id=item_id).count() + 1
    )
    version = models.Version(
        item_type=item_type,
        item_id=item_id,
        version_number=next_version,
        thumbnail_path=f"uploads/{saved_name}",
        original_filename=(file.filename or "")[:MAX_ORIGINAL_FILENAME_LENGTH] or None,
    )
    db.add(version)
    db.commit()
    db.refresh(version)
    return version
