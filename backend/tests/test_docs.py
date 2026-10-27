"""README・ADR・運用手順書が、実態と合っていることのテスト。"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
README = (ROOT / "README.md").read_text(encoding="utf-8")


def test_every_adr_is_listed_in_the_readme_and_there_are_at_least_nine() -> None:
    adrs = sorted((ROOT / "docs" / "adr").glob("*.md"))

    assert len(adrs) >= 9
    for adr in adrs:
        assert f"docs/adr/{adr.name}" in README, adr.name


def test_the_superseded_adr_points_to_its_replacement() -> None:
    old = (ROOT / "docs/adr/0004-no-auth.md").read_text(encoding="utf-8")

    assert "Superseded" in old
    assert "0005" in old


def test_the_readme_images_exist() -> None:
    images = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", README)

    assert len(images) >= 3
    for image in images:
        assert (ROOT / image).is_file(), image


def test_relative_links_in_the_readme_point_to_existing_files() -> None:
    for link in re.findall(r"\]\(((?:docs|\.env)[^)#]*|CHANGELOG\.md|LICENSE)\)", README):
        assert (ROOT / link).exists(), link


def test_the_readme_has_an_english_summary_and_an_architecture_diagram() -> None:
    assert "English summary" in README
    assert "```mermaid" in README


def test_the_operations_manual_covers_backup_restore_and_upgrade() -> None:
    text = (ROOT / "docs/operations.md").read_text(encoding="utf-8")

    for heading in ("## バックアップ", "## 復旧", "## 更新(アップグレード)", "## 起動"):
        assert heading in text
    assert "python -m app.migrate stamp 0001" in text
    assert "s.backup(d)" in text
