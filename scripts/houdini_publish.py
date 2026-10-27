"""Houdini からサムネイル付きでパブリッシュするスクリプト(PipeBoard mini)。

使い方(Houdini Python Shell / hython):
    import sys
    sys.path.append("/path/to/pipeboard/scripts")
    import hou
    from houdini_publish import publish, write_cop_thumbnail
    write_cop_thumbnail(hou, "/tmp/thumb.png")
    publish("http://localhost:8000", "shot", 12, "/tmp/thumb.png",
            report_path="/tmp/report.json", status="in_review")

HTTP の部分は hou に依存せず、`session` を差し替えて検証できる。サムネイルの生成だけが
`hou` を使い、`hou` モジュールは引数で受け取る(CI では偽物、実機では本物)。
検査レポートは、unibridge の `integrity-check --format json` などが出す共通形式。
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Protocol

import requests

ITEM_TYPE_PATHS = {"shot": "shots", "asset": "assets"}
MIME_BY_EXTENSION = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}
REPORT_REQUIRED_KEYS = ("schema_version", "tool", "has_errors", "findings")
TIMEOUT_SECONDS = 30
GATE_BLOCKED_STATUS = 409


class PublishError(RuntimeError):
    pass


class PublishBlocked(PublishError):
    pass


class _HttpSession(Protocol):
    def post(self, url: str, **kwargs: Any) -> Any: ...

    def patch(self, url: str, **kwargs: Any) -> Any: ...


def _headers(token: str | None) -> dict[str, str]:
    api_token = token or os.environ.get("PIPEBOARD_API_TOKEN")
    return {"Authorization": f"Bearer {api_token}"} if api_token else {}


def _item_path(item_type: str) -> str:
    if item_type not in ITEM_TYPE_PATHS:
        raise ValueError(f"Unknown item_type: {item_type!r} (expected 'shot' or 'asset')")
    return ITEM_TYPE_PATHS[item_type]


def _mime_type(path: Path) -> str:
    mime = MIME_BY_EXTENSION.get(path.suffix.lower())
    if mime is None:
        raise ValueError(f"'{path.name}' is not supported: use png, jpg, jpeg or webp")
    return mime


def _problem_title(response: Any) -> str:
    try:
        return str(response.json().get("title", ""))
    except (ValueError, AttributeError):
        return ""


def _checked(response: Any, action: str) -> dict[str, Any]:
    if not response.ok:
        title = _problem_title(response)
        raise PublishError(f"{action} failed: HTTP {response.status_code} {title}".strip())
    body: dict[str, Any] = response.json()
    return body


def publish_version(
    base_url: str,
    item_type: str,
    item_id: int,
    image_path: str | Path,
    session: _HttpSession | None = None,
    token: str | None = None,
) -> dict[str, Any]:
    """画像を新しいバージョンとしてアップロードする。"""
    path = Path(image_path)
    mime = _mime_type(path)
    _item_path(item_type)
    http = session or requests
    url = f"{base_url}/versions?item_type={item_type}&item_id={item_id}"
    response = http.post(
        url,
        files={"file": (path.name, path.read_bytes(), mime)},
        headers=_headers(token),
        timeout=TIMEOUT_SECONDS,
    )
    return _checked(response, "Upload")


def load_check_report(path: str | Path) -> dict[str, Any]:
    try:
        report: dict[str, Any] = json.loads(Path(path).read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"'{path}' is not valid JSON") from exc
    for key in REPORT_REQUIRED_KEYS:
        if key not in report:
            raise ValueError(f"'{path}' is not a check report: missing '{key}'")
    return report


def submit_check(
    base_url: str,
    item_type: str,
    item_id: int,
    report: dict[str, Any],
    session: _HttpSession | None = None,
    token: str | None = None,
) -> dict[str, Any]:
    http = session or requests
    url = f"{base_url}/{_item_path(item_type)}/{item_id}/checks"
    response = http.post(url, json=report, headers=_headers(token), timeout=TIMEOUT_SECONDS)
    return _checked(response, "Check submission")


def update_status(
    base_url: str,
    item_type: str,
    item_id: int,
    status: str,
    session: _HttpSession | None = None,
    token: str | None = None,
) -> dict[str, Any]:
    http = session or requests
    url = f"{base_url}/{_item_path(item_type)}/{item_id}/status"
    response = http.patch(
        url, json={"status": status}, headers=_headers(token), timeout=TIMEOUT_SECONDS
    )
    if response.status_code == GATE_BLOCKED_STATUS:
        raise PublishBlocked(_problem_title(response) or "Publish gate blocked the change")
    return _checked(response, "Status update")


def publish(
    base_url: str,
    item_type: str,
    item_id: int,
    image_path: str | Path,
    *,
    report_path: str | Path | None = None,
    status: str | None = None,
    session: _HttpSession | None = None,
    token: str | None = None,
) -> dict[str, Any]:
    """サムネイルのアップロード → 検査結果の提出 → ステータス変更、の順に行う。

    公開ゲートが止めたときは PublishBlocked を送出する(アップロードと検査結果は、
    すでに登録されている。直して再提出すれば、ゲートを通れる)。
    """
    report = load_check_report(report_path) if report_path is not None else None
    version = publish_version(base_url, item_type, item_id, image_path, session, token)
    check = submit_check(base_url, item_type, item_id, report, session, token) if report else None
    changed = (
        update_status(base_url, item_type, item_id, status, session, token) if status else None
    )
    return {
        "version": version,
        "check": check,
        "status": changed["status"] if changed else None,
    }


def write_cop_thumbnail(
    hou: Any,
    output_path: str | Path,
    width: int = 640,
    height: int = 360,
    color: tuple[float, float, float] = (0.2, 0.3, 0.5),
) -> Path:
    """COP2 の単色画像を PNG などに書き出す(GL を使わないので、hython でも動く)。

    実際のシーンの見た目を使うときは、ここで作った画像の代わりに、ビューポートや
    レンダーの出力ファイルを `publish` に渡す。
    """
    out = Path(output_path)
    _mime_type(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    network = hou.node("/img").createNode("img")
    try:
        source = network.createNode("color")
        for name, value in (
            ("overridesize", 1),
            ("size1", width),
            ("size2", height),
            ("colorr", color[0]),
            ("colorg", color[1]),
            ("colorb", color[2]),
        ):
            source.parm(name).set(value)
        rop = network.createNode("rop_comp")
        rop.parm("coppath").set(source.path())
        rop.parm("copoutput").set(str(out))
        rop.parm("execute").pressButton()
    finally:
        network.destroy()
    return out
