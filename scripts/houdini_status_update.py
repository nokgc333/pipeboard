"""HoudiniのPython ShellからPipeBoard miniのステータスを更新するスクリプト（FR-007）。

使い方（Houdini Python Shell内）:
    import sys
    sys.path.append("/path/to/pipeboard/scripts")
    from houdini_status_update import send_status_update
    send_status_update("http://localhost:8000", "shot", 12, "in_review")

hou には一切依存しない（このファイル自体はHoudini専用の処理を持たず、
どのPython環境からでもrequestsさえあれば実行できる）。そのため、
CIのpytestでHTTP呼び出しロジックを直接検証できる（仕様書§12.5）。
"""

from __future__ import annotations

import os
from typing import Any, Protocol

import requests

ITEM_TYPE_PATHS = {"shot": "shots", "asset": "assets"}


class _HttpSession(Protocol):
    def patch(self, url: str, **kwargs: Any) -> Any: ...


def build_status_update_url(base_url: str, item_type: str, item_id: int) -> str:
    """item_typeに応じたPATCHエンドポイントURLを組み立てる。"""
    if item_type not in ITEM_TYPE_PATHS:
        raise ValueError(f"Unknown item_type: {item_type!r} (expected 'shot' or 'asset')")
    path = ITEM_TYPE_PATHS[item_type]
    return f"{base_url}/{path}/{item_id}/status"


def send_status_update(
    base_url: str,
    item_type: str,
    item_id: int,
    status: str,
    session: _HttpSession | None = None,
    token: str | None = None,
) -> dict[str, Any]:
    """PipeBoard miniのステータス更新APIをPATCHで呼び出す。

    session を注入可能にすることで、実ネットワーク呼び出しなしにpytestで検証できる
    （仕様書§12.5の「HTTP呼び出しロジック部分の分離」方針）。
    """
    http = session or requests
    url = build_status_update_url(base_url, item_type, item_id)
    api_token = token or os.environ.get("PIPEBOARD_API_TOKEN")
    extra: dict[str, Any] = (
        {"headers": {"Authorization": f"Bearer {api_token}"}} if api_token else {}
    )
    response = http.patch(url, json={"status": status}, timeout=5, **extra)
    response.raise_for_status()
    result: dict[str, Any] = response.json()
    return result
