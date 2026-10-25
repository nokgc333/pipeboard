"""PipeBoard backend REST APIへの薄いHTTPクライアント（PySide6は一切importしない）。

`scripts/houdini_status_update.py`と同じ思想: requestsのみに依存し、注入可能な
`session`で実ネットワーク呼び出しなしにpytestで検証できる。backend側のエラーレスポンスは
RFC 9457 (Problem Details, `app/errors.py`)準拠のため、`ApiError`でラップして呼び出し元に
伝える。
"""

from __future__ import annotations

import os
from typing import Any, Protocol

import requests

# shot/asset は同一スキーマだが別テーブル・別URLパス（backend/app/domain/items.py）
ITEM_TYPE_PATHS: dict[str, str] = {"shot": "shots", "asset": "assets"}

_REQUEST_TIMEOUT_SECONDS = 5


class ApiError(Exception):
    """RFC 9457 (Problem Details for HTTP APIs) 準拠のエラーレスポンスをラップする例外。"""

    def __init__(self, status_code: int, title: str, detail: str | None = None) -> None:
        self.status_code = status_code
        self.title = title
        self.detail = detail
        super().__init__(f"{status_code}: {title}")


class _HttpResponse(Protocol):
    status_code: int

    def json(self) -> Any: ...


class _HttpSession(Protocol):
    def get(self, url: str, **kwargs: Any) -> _HttpResponse: ...
    def post(self, url: str, **kwargs: Any) -> _HttpResponse: ...
    def patch(self, url: str, **kwargs: Any) -> _HttpResponse: ...


def _item_path(item_type: str) -> str:
    """item_type("shot"/"asset")をURLパスセグメントに変換する。未知の値は拒否する。"""
    if item_type not in ITEM_TYPE_PATHS:
        raise ValueError(f"Unknown item_type: {item_type!r} (expected 'shot' or 'asset')")
    return ITEM_TYPE_PATHS[item_type]


class PipeBoardApiClient:
    """PipeBoard mini backend(FastAPI)の薄いHTTPクライアント。

    `session`を注入可能にすることで、実HTTP通信なしにテストできる
    （houdini_status_update.pyと同じ設計）。PySide6のウィジェット層(main_window.py)からは
    このクライアントを経由してのみバックエンドと通信する。
    """

    def __init__(
        self,
        base_url: str,
        session: _HttpSession | None = None,
        token: str | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._session = session or requests.Session()
        self._token = token or os.environ.get("PIPEBOARD_API_TOKEN")

    def _request_options(self) -> dict[str, Any]:
        options: dict[str, Any] = {"timeout": _REQUEST_TIMEOUT_SECONDS}
        if self._token:
            options["headers"] = {"Authorization": f"Bearer {self._token}"}
        return options

    def _handle_response(self, response: _HttpResponse) -> Any:
        if not (200 <= response.status_code < 300):
            try:
                problem = response.json()
            except ValueError:
                problem = {}
            title = problem.get("title") or f"Request failed: {response.status_code}"
            raise ApiError(response.status_code, title, problem.get("detail"))
        if response.status_code == 204:
            return None
        return response.json()

    def list_shots(self) -> list[dict[str, Any]]:
        response = self._session.get(f"{self._base_url}/shots", **self._request_options())
        return list(self._handle_response(response))

    def list_assets(self) -> list[dict[str, Any]]:
        response = self._session.get(f"{self._base_url}/assets", **self._request_options())
        return list(self._handle_response(response))

    def update_shot_status(self, shot_id: int, status: str) -> dict[str, Any]:
        """ショットのステータスを更新する（update_item_status("shot", ...)のショートハンド）。"""
        return self.update_item_status("shot", shot_id, status)

    def update_item_status(self, item_type: str, item_id: int, status: str) -> dict[str, Any]:
        path = _item_path(item_type)
        response = self._session.patch(
            f"{self._base_url}/{path}/{item_id}/status",
            json={"status": status},
            **self._request_options(),
        )
        result: dict[str, Any] = self._handle_response(response)
        return result

    def list_versions(self, item_type: str, item_id: int) -> list[dict[str, Any]]:
        path = _item_path(item_type)
        response = self._session.get(
            f"{self._base_url}/{path}/{item_id}/versions", **self._request_options()
        )
        return list(self._handle_response(response))

    def list_comments(self, item_type: str, item_id: int) -> list[dict[str, Any]]:
        path = _item_path(item_type)
        response = self._session.get(
            f"{self._base_url}/{path}/{item_id}/comments", **self._request_options()
        )
        return list(self._handle_response(response))

    def create_comment(
        self, item_type: str, item_id: int, body: str, tag: str | None = None
    ) -> dict[str, Any]:
        response = self._session.post(
            f"{self._base_url}/comments",
            json={"item_type": item_type, "item_id": item_id, "body": body, "tag": tag},
            **self._request_options(),
        )
        result: dict[str, Any] = self._handle_response(response)
        return result
