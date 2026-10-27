"""docs/api.md(OpenAPI から生成する API 一覧)のテスト。"""

from __future__ import annotations

from pathlib import Path

from app.export_api_doc import api_markdown, main

COMMITTED = Path(__file__).resolve().parents[2] / "docs" / "api.md"


def test_the_committed_document_matches_the_running_api() -> None:
    assert (
        COMMITTED.read_text(encoding="utf-8") == api_markdown()
    ), "run: python -m app.export_api_doc ../docs/api.md"


def test_every_route_is_listed_with_its_method_and_path() -> None:
    text = api_markdown()

    for line in (
        "| GET | `/shots` |",
        "| PATCH | `/shots/{item_id}/status` |",
        "| POST | `/shots/{item_id}/checks` |",
        "| PUT | `/shots/{item_id}/sequence` |",
        "| GET | `/audit-log` |",
        "| GET | `/health` |",
    ):
        assert line in text


def test_the_roles_that_each_route_needs_are_shown() -> None:
    text = api_markdown()

    assert "| DELETE | `/shots/{item_id}` | admin |" in text
    assert "| POST | `/shots` | editor |" in text
    assert "| GET | `/shots` | viewer |" in text
    assert "| GET | `/health` | なし |" in text


def test_the_export_writes_the_file_and_usage_is_checked(tmp_path: Path) -> None:
    out = tmp_path / "api.md"

    assert main(["x", str(out)]) == 0
    assert out.read_text(encoding="utf-8") == api_markdown()
    assert main(["x"]) == 2
