"""OpenAPI の書き出しと、フロントエンドに置いた生成元(openapi.json)が最新であることのテスト。"""

from __future__ import annotations

import json
from pathlib import Path

from app.export_openapi import main, openapi_text

COMMITTED = Path(__file__).resolve().parents[2] / "frontend" / "openapi.json"


def test_the_committed_openapi_file_matches_the_running_api() -> None:
    assert (
        COMMITTED.read_text(encoding="utf-8") == openapi_text()
    ), "run: python -m app.export_openapi ../frontend/openapi.json"


def test_the_export_writes_valid_json_with_the_resource_paths(tmp_path: Path) -> None:
    out = tmp_path / "openapi.json"

    assert main(["export", str(out)]) == 0

    paths = json.loads(out.read_text(encoding="utf-8"))["paths"]
    assert {"/shots", "/assets", "/versions", "/comments"} <= set(paths)


def test_the_export_without_an_output_path_prints_usage_and_fails(
    capsys: object,
) -> None:
    assert main(["export"]) == 2


def test_item_status_is_published_as_an_enum_so_clients_get_a_union() -> None:
    schemas = json.loads(openapi_text())["components"]["schemas"]

    assert schemas["ItemOut"]["properties"]["status"]["enum"] == [
        "not_started",
        "in_progress",
        "in_review",
        "done",
    ]
    assert schemas["VersionOut"]["properties"]["item_type"]["enum"] == ["shot", "asset"]
