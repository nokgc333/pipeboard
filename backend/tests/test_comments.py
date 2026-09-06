"""comments router の統合テスト（TC-016〜018）。"""

from fastapi.testclient import TestClient


def test_create_comment_with_tag(client: TestClient) -> None:
    shot_id = client.post("/shots", json={"name": "SHOT010"}).json()["id"]

    response = client.post(
        "/comments",
        json={"item_type": "shot", "item_id": shot_id, "body": "ライティング要調整", "tag": "note"},
    )

    assert response.status_code == 201
    assert response.json()["tag"] == "note"


def test_create_comment_without_tag_defaults_to_none(client: TestClient) -> None:
    shot_id = client.post("/shots", json={"name": "SHOT010"}).json()["id"]

    response = client.post(
        "/comments", json={"item_type": "shot", "item_id": shot_id, "body": "OK"}
    )

    assert response.json()["tag"] is None


def test_empty_body_is_rejected(client: TestClient) -> None:
    """TC-017: 1〜2000文字のバリデーション（空文字は拒否）。"""
    shot_id = client.post("/shots", json={"name": "SHOT010"}).json()["id"]

    response = client.post("/comments", json={"item_type": "shot", "item_id": shot_id, "body": ""})

    assert response.status_code == 422


def test_body_over_2000_chars_is_rejected(client: TestClient) -> None:
    shot_id = client.post("/shots", json={"name": "SHOT010"}).json()["id"]

    response = client.post(
        "/comments",
        json={"item_type": "shot", "item_id": shot_id, "body": "x" * 2001},
    )

    assert response.status_code == 422


def test_list_comments_returns_chronological_order(client: TestClient) -> None:
    """TC-018: コメント一覧は時系列昇順で返る。"""
    shot_id = client.post("/shots", json={"name": "SHOT010"}).json()["id"]
    client.post("/comments", json={"item_type": "shot", "item_id": shot_id, "body": "first"})
    client.post("/comments", json={"item_type": "shot", "item_id": shot_id, "body": "second"})

    response = client.get(f"/shots/{shot_id}/comments")

    bodies = [c["body"] for c in response.json()]
    assert bodies == ["first", "second"]
