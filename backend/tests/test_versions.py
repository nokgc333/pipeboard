"""versions router の統合テスト（TC-009〜015）。"""

import io

from fastapi.testclient import TestClient

PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0"
    b"\x00\x00\x03\x01\x01\x00\x18\xdd\x8d\xb0\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _upload(client: TestClient, item_id: int, filename: str, content_type: str, data: bytes):
    return client.post(
        f"/versions?item_type=shot&item_id={item_id}",
        files={"file": (filename, io.BytesIO(data), content_type)},
    )


class TestUploadVersion:
    def test_valid_png_upload_returns_version_1(self, client: TestClient) -> None:
        shot_id = client.post("/shots", json={"name": "SHOT010"}).json()["id"]

        response = _upload(client, shot_id, "render.png", "image/png", PNG_BYTES)

        assert response.status_code == 201
        body = response.json()
        assert body["version_number"] == 1
        assert body["item_type"] == "shot"
        assert body["thumbnail_path"].startswith("uploads/")
        assert body["thumbnail_path"].endswith(".png")

    def test_second_upload_for_same_item_increments_version(self, client: TestClient) -> None:
        shot_id = client.post("/shots", json={"name": "SHOT010"}).json()["id"]
        _upload(client, shot_id, "v1.png", "image/png", PNG_BYTES)

        second = _upload(client, shot_id, "v2.png", "image/png", PNG_BYTES)

        assert second.json()["version_number"] == 2

    def test_rejects_disallowed_extension(self, client: TestClient) -> None:
        """TC-011: 拡張子がホワイトリスト外の場合400を返す。"""
        shot_id = client.post("/shots", json={"name": "SHOT010"}).json()["id"]

        response = _upload(client, shot_id, "malware.exe", "application/octet-stream", b"x")

        assert response.status_code == 400

    def test_rejects_mismatched_mime_type_for_allowed_extension(self, client: TestClient) -> None:
        """TC-012: 拡張子はpngでもContent-Typeが偽装されている場合は拒否する（なりすまし対策）。"""
        shot_id = client.post("/shots", json={"name": "SHOT010"}).json()["id"]

        response = _upload(client, shot_id, "fake.png", "application/octet-stream", PNG_BYTES)

        assert response.status_code == 400

    def test_rejects_file_larger_than_10mb(self, client: TestClient) -> None:
        """TC-013: 10MB超のファイルは413を返す。"""
        shot_id = client.post("/shots", json={"name": "SHOT010"}).json()["id"]
        oversized = b"\x00" * (10 * 1024 * 1024 + 1)

        response = _upload(client, shot_id, "huge.png", "image/png", oversized)

        assert response.status_code == 413

    def test_list_versions_returns_newest_first(self, client: TestClient) -> None:
        """TC-014: バージョン一覧は新しい順（version_number降順）で返る。"""
        shot_id = client.post("/shots", json={"name": "SHOT010"}).json()["id"]
        _upload(client, shot_id, "v1.png", "image/png", PNG_BYTES)
        _upload(client, shot_id, "v2.png", "image/png", PNG_BYTES)

        response = client.get(f"/shots/{shot_id}/versions")

        numbers = [v["version_number"] for v in response.json()]
        assert numbers == [2, 1]

    def test_shot_and_asset_versions_are_counted_independently(self, client: TestClient) -> None:
        """TC-015: item_typeが異なれば同じitem_idでもバージョン採番は独立する。"""
        shot_id = client.post("/shots", json={"name": "SHOT010"}).json()["id"]
        asset_id = client.post("/assets", json={"name": "Prop_Chair"}).json()["id"]

        shot_upload = _upload(client, shot_id, "s.png", "image/png", PNG_BYTES)
        asset_response = client.post(
            f"/versions?item_type=asset&item_id={asset_id}",
            files={"file": ("a.png", io.BytesIO(PNG_BYTES), "image/png")},
        )

        assert shot_upload.json()["version_number"] == 1
        assert asset_response.json()["version_number"] == 1
