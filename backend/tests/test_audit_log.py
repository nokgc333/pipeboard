"""監査ログ(誰が・いつ・何を)のテスト。"""

from __future__ import annotations

import io
import json
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0"
    b"\x00\x00\x03\x01\x01\x00\x18\xdd\x8d\xb0\x00\x00\x00\x00IEND\xaeB`\x82"
)
TOKENS = "viewer=view-token-0001,editor=edit-token-0002,admin=admin-token-0003"


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _log(client: TestClient, query: str = "") -> list[dict[str, object]]:
    return client.get(f"/audit-log{query}").json()  # type: ignore[no-any-return]


def _actions(client: TestClient, query: str = "") -> list[str]:
    return [str(e["action"]) for e in _log(client, query)]


def test_creating_a_shot_is_recorded_with_its_name(client: TestClient) -> None:
    shot_id = client.post("/shots", json={"name": "SHOT010"}).json()["id"]

    entry = _log(client)[0]

    assert entry["action"] == "shot.create"
    assert entry["item_type"] == "shot"
    assert entry["item_id"] == shot_id
    assert json.loads(str(entry["detail"])) == {"name": "SHOT010"}
    assert entry["actor"] == "admin"
    assert entry["created_at"]


def test_a_status_change_records_the_old_and_new_status(client: TestClient) -> None:
    shot_id = client.post("/shots", json={"name": "SHOT010"}).json()["id"]
    client.patch(f"/shots/{shot_id}/status", json={"status": "in_review"})

    entry = _log(client)[0]

    assert entry["action"] == "shot.status"
    assert json.loads(str(entry["detail"])) == {"from": "not_started", "to": "in_review"}


def test_a_rename_records_the_old_and_new_name(client: TestClient) -> None:
    shot_id = client.post("/shots", json={"name": "SHOT010"}).json()["id"]
    client.put(f"/shots/{shot_id}", json={"name": "SHOT011"})

    entry = _log(client)[0]

    assert entry["action"] == "shot.rename"
    assert json.loads(str(entry["detail"])) == {"from": "SHOT010", "to": "SHOT011"}


def test_deleting_an_item_is_recorded_even_though_its_rows_are_gone(client: TestClient) -> None:
    shot_id = client.post("/shots", json={"name": "SHOT010"}).json()["id"]
    client.delete(f"/shots/{shot_id}")

    assert _actions(client)[0] == "shot.delete"


def test_a_comment_and_an_upload_are_recorded_against_their_item(client: TestClient) -> None:
    asset_id = client.post("/assets", json={"name": "Prop"}).json()["id"]
    client.post("/comments", json={"item_type": "asset", "item_id": asset_id, "body": "ok"})
    client.post(
        f"/versions?item_type=asset&item_id={asset_id}",
        files={"file": ("a.png", io.BytesIO(PNG_BYTES), "image/png")},
    )

    entries = _log(client, f"?item_type=asset&item_id={asset_id}")

    assert [e["action"] for e in entries] == ["version.upload", "comment.create", "asset.create"]


def test_failed_requests_leave_no_trace(client: TestClient) -> None:
    shot_id = client.post("/shots", json={"name": "SHOT010"}).json()["id"]
    before = len(_log(client))

    client.patch(f"/shots/{shot_id}/status", json={"status": "archived"})
    client.patch("/shots/9999/status", json={"status": "done"})
    client.post("/comments", json={"item_type": "shot", "item_id": 9999, "body": "x"})

    assert len(_log(client)) == before


def test_reading_does_not_write_to_the_log(client: TestClient) -> None:
    client.post("/shots", json={"name": "SHOT010"})
    before = len(_log(client))

    client.get("/shots")
    client.get("/shots/1")

    assert len(_log(client)) == before


def test_the_log_is_newest_first_and_can_be_paged_and_filtered(client: TestClient) -> None:
    for name in ("A", "B", "C"):
        client.post("/shots", json={"name": name})
    client.post("/assets", json={"name": "Prop"})

    response = client.get("/audit-log?limit=2")

    assert [json.loads(e["detail"])["name"] for e in response.json()] == ["Prop", "C"]
    assert response.headers["X-Total-Count"] == "4"
    assert _actions(client, "?action=asset.create") == ["asset.create"]
    assert len(_log(client, "?offset=3")) == 1


@pytest.fixture()
def token_mode(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("PIPEBOARD_AUTH_MODE", "token")
    monkeypatch.setenv("PIPEBOARD_API_TOKENS", TOKENS)
    yield


@pytest.mark.usefixtures("token_mode")
class TestInTokenMode:
    def test_the_actor_is_the_role_of_the_token(self, client: TestClient) -> None:
        client.post("/shots", json={"name": "SHOT010"}, headers=_bearer("edit-token-0002"))

        entry = client.get("/audit-log", headers=_bearer("admin-token-0003")).json()[0]

        assert entry["actor"] == "editor"

    @pytest.mark.parametrize("token", ["view-token-0001", "edit-token-0002"])
    def test_only_an_admin_can_read_the_log(self, client: TestClient, token: str) -> None:
        assert client.get("/audit-log", headers=_bearer(token)).status_code == 403

    def test_a_request_without_a_token_is_rejected(self, client: TestClient) -> None:
        assert client.get("/audit-log").status_code == 401

    def test_a_refused_write_is_not_logged(self, client: TestClient) -> None:
        client.post("/shots", json={"name": "SHOT010"}, headers=_bearer("view-token-0001"))

        assert client.get("/audit-log", headers=_bearer("admin-token-0003")).json() == []
