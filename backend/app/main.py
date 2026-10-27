"""PipeBoard mini APIエントリポイント（仕様書§5.3参照）。"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.exceptions import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app import rate_limit, webhooks
from app.auth import load_auth_settings
from app.cors import load_allowed_origins
from app.database import get_db
from app.errors import problem_details_handler
from app.gate_settings import load_required_checks
from app.routers import assets, audit_log, comments, hierarchy, shots, versions


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    load_auth_settings()
    rate_limit.load_limits()
    webhooks.load_webhook_settings()
    load_required_checks()
    yield


app = FastAPI(
    title="PipeBoard mini API",
    version="0.2.0",
    lifespan=lifespan,
    dependencies=[Depends(rate_limit.enforce_rate_limit)],
)

app.add_exception_handler(HTTPException, problem_details_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=load_allowed_origins(),
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
    allow_credentials=False,
    expose_headers=["X-Total-Count"],
)

app.include_router(shots.router, prefix="/shots", tags=["shots"])
app.include_router(assets.router, prefix="/assets", tags=["assets"])
app.include_router(versions.router, prefix="/versions", tags=["versions"])
app.include_router(comments.router, prefix="/comments", tags=["comments"])
app.include_router(hierarchy.projects_router, prefix="/projects", tags=["projects"])
app.include_router(hierarchy.sequences_router, prefix="/sequences", tags=["projects"])
app.include_router(audit_log.router, prefix="/audit-log", tags=["audit"])


@app.get("/health")
def health(db: Session = Depends(get_db)) -> dict[str, str]:
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001 - どんな接続障害でも 503 にする
        raise HTTPException(status_code=503, detail="Database unavailable") from exc
    return {"status": "ok", "database": "ok", "version": app.version}


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}
