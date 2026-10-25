import io

import pytest
from fastapi.testclient import TestClient

from tests.test_versions import PNG_BYTES

JPEG_BYTES = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xd9"
WEBP_BYTES = b"RIFF\x1a\x00\x00\x00WEBPVP8 \x0e\x00\x00\x000\x01\x00\x9d\x01*\x01\x00\x01\x00"


def _upload(client: TestClient, item_id: int, name: str, content_type: str, data: bytes):
    return client.post(
        f"/versions?item_type=shot&item_id={item_id}",
        files={"file": (name, io.BytesIO(data), content_type)},
    )


@pytest.fixture()
def shot_id(client: TestClient) -> int:
    return int(client.post("/shots", json={"name": "SHOT010"}).json()["id"])


class TestMagicBytes:
    @pytest.mark.parametrize(
        ("name", "content_type", "data"),
        [
            ("a.png", "image/png", PNG_BYTES),
            ("a.jpg", "image/jpeg", JPEG_BYTES),
            ("a.jpeg", "image/jpeg", JPEG_BYTES),
            ("a.webp", "image/webp", WEBP_BYTES),
        ],
    )
    def test_matching_signatures_are_accepted(
        self, client: TestClient, shot_id: int, name: str, content_type: str, data: bytes
    ) -> None:
        assert _upload(client, shot_id, name, content_type, data).status_code == 201

    def test_text_content_declared_as_png_is_rejected(
        self, client: TestClient, shot_id: int
    ) -> None:
        response = _upload(client, shot_id, "evil.png", "image/png", b"<script>alert(1)</script>")

        assert response.status_code == 400

    def test_a_signature_that_does_not_match_the_extension_is_rejected(
        self, client: TestClient, shot_id: int
    ) -> None:
        response = _upload(client, shot_id, "a.jpg", "image/jpeg", PNG_BYTES)

        assert response.status_code == 400

    def test_an_empty_file_is_rejected(self, client: TestClient, shot_id: int) -> None:
        assert _upload(client, shot_id, "a.png", "image/png", b"").status_code == 400

    def test_a_rejected_file_is_not_stored(
        self, client: TestClient, shot_id: int, tmp_path
    ) -> None:
        _upload(client, shot_id, "evil.png", "image/png", b"not an image")

        assert not (tmp_path / "uploads").exists() or list((tmp_path / "uploads").iterdir()) == []


class TestItemTypeValidation:
    def test_unknown_item_type_is_rejected_on_upload(self, client: TestClient) -> None:
        response = client.post(
            "/versions?item_type=../etc&item_id=1",
            files={"file": ("a.png", io.BytesIO(PNG_BYTES), "image/png")},
        )

        assert response.status_code == 422

    def test_unknown_item_type_is_rejected_on_comment(self, client: TestClient) -> None:
        response = client.post(
            "/comments", json={"item_type": "scene", "item_id": 1, "body": "hello"}
        )

        assert response.status_code == 422


class TestInputLimits:
    def test_item_name_over_100_chars_is_rejected(self, client: TestClient) -> None:
        assert client.post("/shots", json={"name": "x" * 101}).status_code == 422

    def test_comment_tag_over_30_chars_is_rejected(self, client: TestClient, shot_id: int) -> None:
        response = client.post(
            "/comments",
            json={"item_type": "shot", "item_id": shot_id, "body": "ok", "tag": "t" * 31},
        )

        assert response.status_code == 422

    def test_original_filename_is_truncated_to_the_column_limit(
        self, client: TestClient, shot_id: int
    ) -> None:
        response = _upload(client, shot_id, "a" * 400 + ".png", "image/png", PNG_BYTES)

        assert response.status_code == 201
        assert len(response.json()["original_filename"]) <= 255
