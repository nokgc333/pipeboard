"""アップロード済み画像の配信。

`<img>` はヘッダでトークンを送れないため、認証なしで取得できる。名前は UUID4 で推測できず
(能力 URL)、画像の拡張子だけを許し、任意のパスは受け付けない(ADR-0006)。
"""

from __future__ import annotations

import re

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse

from app.routers.versions import ALLOWED_EXTENSIONS, upload_dir

router = APIRouter()

SAFE_NAME = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}(\.[a-z]+)$")
MEDIA_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}
CACHE_CONTROL = "public, max-age=31536000, immutable"


@router.get("/{filename}")
def get_upload(filename: str) -> FileResponse:
    match = SAFE_NAME.match(filename)
    if match is None or match.group(1) not in ALLOWED_EXTENSIONS:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")
    path = upload_dir() / filename
    if not path.is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")
    return FileResponse(
        path,
        media_type=MEDIA_TYPES[match.group(1)],
        headers={"X-Content-Type-Options": "nosniff", "Cache-Control": CACHE_CONTROL},
    )
