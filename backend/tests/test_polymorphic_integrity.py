"""versions / comments が、存在しない対象を指さないことのテスト(ADR-0002: DB の外部キーが無い代わり)。"""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0"
    b"\x00\x00\x03\x01\x01\x00\x18\xdd\x8d\xb0\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _comment(client: TestClient, item_type: str, item_id: int):  # type: ignore[no-untyped-def]
    return client.post(
        "/comments", json={"item_type": item_type, "item_id": item_id, "body": "memo"}
    )


def _upload(client: TestClient, item_type: str, item_id: int):  # type: ignore[no-untyped-def]
    return client.post(
        f"/versions?item_type={item_type}&item_id={item_id}",
        files={"file": ("a.png", io.BytesIO(PNG_BYTES), "image/png")},
    )


@pytest.mark.parametrize("item_type", ["shot", "asset"])
def test_a_comment_on_a_missing_item_is_rejected_with_404(
    client: TestClient, item_type: str
) -> None:
    response = _comment(client, item_type, 9999)

    assert response.status_code == 404
    assert "9999" in response.json()["title"]


@pytest.mark.parametrize("item_type", ["shot", "asset"])
def test_an_upload_to_a_missing_item_is_rejected_with_404(
    client: TestClient, item_type: str
) -> None:
    assert _upload(client, item_type, 9999).status_code == 404


def test_a_rejected_upload_leaves_no_file_behind(client: TestClient, tmp_path: Path) -> None:
    _upload(client, "shot", 9999)

    upload_dir = tmp_path / "uploads"
    assert not upload_dir.exists() or list(upload_dir.iterdir()) == []


def test_the_item_type_decides_which_table_is_checked(client: TestClient) -> None:
    shot_id = client.post("/shots", json={"name": "SHOT010"}).json()["id"]

    assert _comment(client, "shot", shot_id).status_code == 201
    assert _comment(client, "asset", shot_id).status_code == 404


def test_a_comment_on_an_existing_asset_is_accepted(client: TestClient) -> None:
    asset_id = client.post("/assets", json={"name": "Prop"}).json()["id"]

    assert _comment(client, "asset", asset_id).status_code == 201


def test_deleting_an_item_removes_its_versions_and_comments_only(client: TestClient) -> None:
    shot_id = client.post("/shots", json={"name": "SHOT010"}).json()["id"]
    asset_id = client.post("/assets", json={"name": "Prop"}).json()["id"]
    assert shot_id == asset_id
    _upload(client, "shot", shot_id)
    _comment(client, "shot", shot_id)
    _upload(client, "asset", asset_id)
    _comment(client, "asset", asset_id)

    assert client.delete(f"/shots/{shot_id}").status_code == 204

    assert len(client.get(f"/assets/{asset_id}/versions").json()) == 1
    assert len(client.get(f"/assets/{asset_id}/comments").json()) == 1
    assert client.get(f"/shots/{shot_id}/versions").status_code == 404
