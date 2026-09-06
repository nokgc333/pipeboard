"""PipeBoard mini APIエントリポイント（仕様書§5.3参照）。"""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.exceptions import HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.errors import problem_details_handler
from app.routers import assets, comments, shots, versions

Base.metadata.create_all(bind=engine)

app = FastAPI(title="PipeBoard mini API", version="0.1.0")

app.add_exception_handler(HTTPException, problem_details_handler)

# 開発時は緩め、デモ公開時はPIPEBOARD_CORS_ORIGINSで許可Originを限定する（SEC-005）
_cors_origins = os.environ.get("PIPEBOARD_CORS_ORIGINS", "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[_cors_origins] if _cors_origins != "*" else ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(shots.router, prefix="/shots", tags=["shots"])
app.include_router(assets.router, prefix="/assets", tags=["assets"])
app.include_router(versions.router, prefix="/versions", tags=["versions"])
app.include_router(comments.router, prefix="/comments", tags=["comments"])


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}
