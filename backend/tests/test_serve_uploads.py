"""アップロードした画像を、ブラウザの <img> から取得できることのテスト。"""

from __future__ import annotations

import io

import pytest
from fastapi.testclient import TestClient

PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0"
    b"\x00\x00\x03\x01\x01\x00\x18\xdd\x8d\xb0\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _upload(client: TestClient) -> str:
    shot_id = client.post("/shots", json={"name": "SHOT010"}).json()["id"]
    response = client.post(
        f"/versions?item_type=shot&item_id={shot_id}",
        files={"file": ("a.png", io.BytesIO(PNG_BYTES), "image/png")},
    )
    return str(response.json()["thumbnail_path"])


def test_the_path_stored_in_the_version_can_be_fetched(client: TestClient) -> None:
    path = _upload(client)

    response = client.get(f"/{path}")

    assert response.status_code == 200
    assert response.content == PNG_BYTES
    assert response.headers["content-type"] == "image/png"


def test_the_response_forbids_sniffing_and_allows_caching(client: TestClient) -> None:
    path = _upload(client)

    headers = client.get(f"/{path}").headers

    assert headers["x-content-type-options"] == "nosniff"
    assert "max-age" in headers["cache-control"]


@pytest.mark.parametrize(
    "name",
    [
        "missing.png",
        "00000000-0000-0000-0000-000000000000.png",
        "..%2Fpipeboard.db",
        "%2e%2e%2f%2e%2e%2fetc%2fpasswd",
        "a.png%00.txt",
        "notauuid.txt",
    ],
)
def test_anything_that_is_not_an_uploaded_image_is_404(client: TestClient, name: str) -> None:
    assert client.get(f"/uploads/{name}").status_code == 404


def test_a_file_with_an_allowed_name_but_a_wrong_extension_is_not_served(
    client: TestClient, tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    import os
    from pathlib import Path

    folder = Path(os.environ["PIPEBOARD_UPLOAD_DIR"])
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "11111111-1111-4111-8111-111111111111.html").write_text("<script>1</script>")

    assert client.get("/uploads/11111111-1111-4111-8111-111111111111.html").status_code == 404


@pytest.fixture()
def token_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PIPEBOARD_AUTH_MODE", "token")
    monkeypatch.setenv("PIPEBOARD_API_TOKENS", "editor=edit-token-0002,admin=admin-token-0003")


@pytest.mark.usefixtures("token_mode")
def test_images_load_in_token_mode_without_a_header_because_img_tags_cannot_send_one(
    client: TestClient,
) -> None:
    editor = {"Authorization": "Bearer edit-token-0002"}
    shot_id = client.post("/shots", json={"name": "S"}, headers=editor).json()["id"]
    path = client.post(
        f"/versions?item_type=shot&item_id={shot_id}",
        files={"file": ("a.png", io.BytesIO(PNG_BYTES), "image/png")},
        headers=editor,
    ).json()["thumbnail_path"]

    assert client.get(f"/{path}").status_code == 200
