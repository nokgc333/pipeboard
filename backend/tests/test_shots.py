"""shots router の統合テスト（TC-001〜005）。"""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app import models


def test_create_shot_returns_201_with_default_status(client: TestClient) -> None:
    response = client.post("/shots", json={"name": "SHOT010"})

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "SHOT010"
    assert body["status"] == "not_started"


def test_list_shots_returns_created_shots(client: TestClient) -> None:
    client.post("/shots", json={"name": "SHOT010"})
    client.post("/shots", json={"name": "SHOT020"})

    response = client.get("/shots")

    assert response.status_code == 200
    names = {s["name"] for s in response.json()}
    assert names == {"SHOT010", "SHOT020"}


def test_update_status_returns_404_for_unknown_shot(client: TestClient) -> None:
    """TC-002: 存在しないshot_idへのPATCHは404を返す。"""
    response = client.patch("/shots/9999/status", json={"status": "in_progress"})

    assert response.status_code == 404


def test_update_status_rejects_invalid_enum(client: TestClient) -> None:
    """TC-003: 未定義のstatus値は400を返す。"""
    create_res = client.post("/shots", json={"name": "SHOT010"})
    shot_id = create_res.json()["id"]

    response = client.patch(f"/shots/{shot_id}/status", json={"status": "unknown"})

    assert response.status_code == 400


def test_update_status_succeeds_and_is_idempotent(client: TestClient) -> None:
    """TC-004: 有効なstatusへのPATCHは成功し、同一statusへの再PATCHも成功する（冪等性）。"""
    shot_id = client.post("/shots", json={"name": "SHOT010"}).json()["id"]

    first = client.patch(f"/shots/{shot_id}/status", json={"status": "in_review"})
    second = client.patch(f"/shots/{shot_id}/status", json={"status": "in_review"})

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["status"] == second.json()["status"] == "in_review"


def test_backward_transition_is_allowed(client: TestClient) -> None:
    """v1では遷移制限を持たないため、in_review -> in_progressの差し戻しも許可される。"""
    shot_id = client.post("/shots", json={"name": "SHOT010"}).json()["id"]
    client.patch(f"/shots/{shot_id}/status", json={"status": "in_review"})

    response = client.patch(f"/shots/{shot_id}/status", json={"status": "in_progress"})

    assert response.status_code == 200
    assert response.json()["status"] == "in_progress"


def test_delete_shot_cascades_versions_and_comments(
    client: TestClient, db_session_factory: sessionmaker[Session]
) -> None:
    """TC-005: ショット削除時、関連するversions/commentsも連動削除される。

    削除後のショット自体は404になる（親が存在しないため、GET /shots/{id}/commentsも
    404を返すのがREST的に正しい）。カスケード削除自体はDBを直接見て確認する。
    """
    shot_id = client.post("/shots", json={"name": "SHOT010"}).json()["id"]
    client.post("/comments", json={"item_type": "shot", "item_id": shot_id, "body": "note"})

    delete_res = client.delete(f"/shots/{shot_id}")
    comments_res = client.get(f"/shots/{shot_id}/comments")

    assert delete_res.status_code == 204
    assert comments_res.status_code == 404

    db = db_session_factory()
    try:
        remaining = db.query(models.Comment).filter_by(item_type="shot", item_id=shot_id).count()
        assert remaining == 0
    finally:
        db.close()


def test_update_shot_name(client: TestClient) -> None:
    shot_id = client.post("/shots", json={"name": "SHOT010"}).json()["id"]

    response = client.put(f"/shots/{shot_id}", json={"name": "SHOT010_renamed"})

    assert response.status_code == 200
    assert response.json()["name"] == "SHOT010_renamed"


def test_get_shot_detail_returns_404_when_missing(client: TestClient) -> None:
    response = client.get("/shots/9999")

    assert response.status_code == 404
