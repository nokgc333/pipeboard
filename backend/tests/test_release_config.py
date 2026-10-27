"""配布と運用の設定(版・Docker・環境変数の見本)が、実態と合っていることのテスト。"""

from __future__ import annotations

import json
import re
from pathlib import Path

from app.main import app

ROOT = Path(__file__).resolve().parents[2]
APP_DIR = ROOT / "backend" / "app"


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_the_api_the_frontend_and_the_changelog_agree_on_the_version() -> None:
    package = json.loads(_read("frontend/package.json"))

    assert package["version"] == app.version
    assert f"## [{app.version}]" in _read("CHANGELOG.md")


def test_every_environment_variable_the_backend_reads_is_in_the_example_file() -> None:
    used = set()
    for path in APP_DIR.rglob("*.py"):
        used |= set(re.findall(r"PIPEBOARD_[A-Z_]+", path.read_text(encoding="utf-8")))
    used -= {"PIPEBOARD_TEST_POSTGRES_URL"}

    example = _read(".env.example")

    missing = sorted(name for name in used if name not in example)
    assert missing == []


def test_the_backend_image_installs_hashed_locked_dependencies_and_runs_as_non_root() -> None:
    dockerfile = _read("backend/Dockerfile")

    assert "--require-hashes -r requirements-runtime.lock" in dockerfile
    assert "USER pipeboard" in dockerfile
    assert "HEALTHCHECK" in dockerfile
    assert "/health" in dockerfile


def test_the_lock_file_pins_every_runtime_dependency_with_hashes() -> None:
    lock = _read("backend/requirements-runtime.lock")

    for name in ("fastapi", "sqlalchemy", "alembic", "uvicorn", "pydantic"):
        assert re.search(rf"^{name}==", lock, re.MULTILINE), name
    assert "--hash=sha256:" in lock


def test_compose_waits_for_a_healthy_backend_before_starting_the_frontend() -> None:
    compose = _read("docker-compose.yml")

    assert "healthcheck:" in compose
    assert "condition: service_healthy" in compose
    assert "/health" in compose


def test_the_release_workflow_publishes_both_images_to_ghcr_from_a_tag() -> None:
    release = _read(".github/workflows/release.yml")

    assert 'tags: ["v*"]' in release
    assert "ghcr.io" in release
    assert "backend, frontend" in release
    assert "packages: write" in release


def test_node_is_pinned_for_local_use_and_for_the_package() -> None:
    assert _read(".nvmrc").strip() == "22"
    assert json.loads(_read("frontend/package.json"))["engines"]["node"] == ">=22"


def test_automatic_updates_cover_every_ecosystem_in_the_repository() -> None:
    dependabot = _read(".github/dependabot.yml")

    for ecosystem in ("pip", "npm", "docker", "github-actions"):
        assert f"package-ecosystem: {ecosystem}" in dependabot
