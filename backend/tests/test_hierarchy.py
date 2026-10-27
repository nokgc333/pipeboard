"""プロジェクト / シーケンスの階層(プロジェクト > シーケンス > ショット)のテスト。"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

TOKENS = "viewer=view-token-0001,editor=edit-token-0002,admin=admin-token-0003"


def _project(client: TestClient, name: str = "ProjA") -> int:
    return int(client.post("/projects", json={"name": name}).json()["id"])


def _sequence(client: TestClient, project_id: int, name: str = "SEQ010") -> int:
    response = client.post(f"/projects/{project_id}/sequences", json={"name": name})
    return int(response.json()["id"])


def _shot(client: TestClient, name: str = "SHOT010") -> int:
    return int(client.post("/shots", json={"name": name}).json()["id"])


class TestProjects:
    def test_a_project_can_be_created_and_listed_newest_first(self, client: TestClient) -> None:
        _project(client, "A")
        _project(client, "B")

        assert [p["name"] for p in client.get("/projects").json()] == ["B", "A"]

    def test_a_duplicate_name_is_a_conflict(self, client: TestClient) -> None:
        _project(client, "A")

        assert client.post("/projects", json={"name": "A"}).status_code == 409

    @pytest.mark.parametrize("name", ["", "x" * 101])
    def test_a_name_must_be_1_to_100_characters(self, client: TestClient, name: str) -> None:
        assert client.post("/projects", json={"name": name}).status_code == 422

    def test_an_empty_project_can_be_deleted(self, client: TestClient) -> None:
        project_id = _project(client)

        assert client.delete(f"/projects/{project_id}").status_code == 204
        assert client.get("/projects").json() == []

    def test_a_project_with_sequences_cannot_be_deleted(self, client: TestClient) -> None:
        project_id = _project(client)
        _sequence(client, project_id)

        assert client.delete(f"/projects/{project_id}").status_code == 409

    def test_deleting_a_missing_project_gives_404(self, client: TestClient) -> None:
        assert client.delete("/projects/9999").status_code == 404


class TestSequences:
    def test_sequences_belong_to_their_project(self, client: TestClient) -> None:
        a = _project(client, "A")
        b = _project(client, "B")
        _sequence(client, a, "SEQ010")
        _sequence(client, b, "SEQ020")

        assert [s["name"] for s in client.get(f"/projects/{a}/sequences").json()] == ["SEQ010"]

    def test_the_same_sequence_name_can_exist_in_different_projects(
        self, client: TestClient
    ) -> None:
        a = _project(client, "A")
        b = _project(client, "B")

        assert client.post(f"/projects/{a}/sequences", json={"name": "SEQ010"}).status_code == 201
        assert client.post(f"/projects/{b}/sequences", json={"name": "SEQ010"}).status_code == 201

    def test_a_duplicate_name_in_one_project_is_a_conflict(self, client: TestClient) -> None:
        a = _project(client)
        _sequence(client, a, "SEQ010")

        assert client.post(f"/projects/{a}/sequences", json={"name": "SEQ010"}).status_code == 409

    def test_a_sequence_of_a_missing_project_gives_404(self, client: TestClient) -> None:
        assert client.post("/projects/9999/sequences", json={"name": "S"}).status_code == 404
        assert client.get("/projects/9999/sequences").status_code == 404

    def test_a_sequence_with_shots_cannot_be_deleted(self, client: TestClient) -> None:
        sequence_id = _sequence(client, _project(client))
        shot_id = _shot(client)
        client.put(f"/shots/{shot_id}/sequence", json={"sequence_id": sequence_id})

        assert client.delete(f"/sequences/{sequence_id}").status_code == 409

    def test_an_empty_sequence_can_be_deleted(self, client: TestClient) -> None:
        project_id = _project(client)
        sequence_id = _sequence(client, project_id)

        assert client.delete(f"/sequences/{sequence_id}").status_code == 204
        assert client.get(f"/projects/{project_id}/sequences").json() == []


class TestShotsInSequences:
    def test_a_shot_starts_without_a_sequence(self, client: TestClient) -> None:
        shot_id = _shot(client)

        assert client.get(f"/shots/{shot_id}").json()["sequence_id"] is None

    def test_a_shot_can_be_moved_into_a_sequence_and_out_again(self, client: TestClient) -> None:
        sequence_id = _sequence(client, _project(client))
        shot_id = _shot(client)

        moved = client.put(f"/shots/{shot_id}/sequence", json={"sequence_id": sequence_id})
        cleared = client.put(f"/shots/{shot_id}/sequence", json={"sequence_id": None})

        assert moved.json()["sequence_id"] == sequence_id
        assert cleared.json()["sequence_id"] is None

    def test_a_missing_sequence_is_rejected(self, client: TestClient) -> None:
        shot_id = _shot(client)

        response = client.put(f"/shots/{shot_id}/sequence", json={"sequence_id": 9999})

        assert response.status_code == 404
        assert client.get(f"/shots/{shot_id}").json()["sequence_id"] is None

    def test_a_missing_shot_is_rejected(self, client: TestClient) -> None:
        assert client.put("/shots/9999/sequence", json={"sequence_id": None}).status_code == 404

    def test_the_shot_list_can_be_filtered_by_sequence(self, client: TestClient) -> None:
        project_id = _project(client)
        first = _sequence(client, project_id, "SEQ010")
        second = _sequence(client, project_id, "SEQ020")
        a = _shot(client, "A")
        b = _shot(client, "B")
        _shot(client, "C")
        client.put(f"/shots/{a}/sequence", json={"sequence_id": first})
        client.put(f"/shots/{b}/sequence", json={"sequence_id": second})

        response = client.get(f"/shots?sequence_id={first}")

        assert [s["name"] for s in response.json()] == ["A"]
        assert response.headers["X-Total-Count"] == "1"

    def test_moving_a_shot_is_recorded_in_the_audit_log(self, client: TestClient) -> None:
        sequence_id = _sequence(client, _project(client))
        shot_id = _shot(client)
        client.put(f"/shots/{shot_id}/sequence", json={"sequence_id": sequence_id})

        assert client.get("/audit-log").json()[0]["action"] == "shot.sequence"

    def test_deleting_a_shot_does_not_touch_its_sequence(self, client: TestClient) -> None:
        project_id = _project(client)
        sequence_id = _sequence(client, project_id)
        shot_id = _shot(client)
        client.put(f"/shots/{shot_id}/sequence", json={"sequence_id": sequence_id})

        client.delete(f"/shots/{shot_id}")

        assert len(client.get(f"/projects/{project_id}/sequences").json()) == 1


@pytest.fixture()
def token_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PIPEBOARD_AUTH_MODE", "token")
    monkeypatch.setenv("PIPEBOARD_API_TOKENS", TOKENS)


@pytest.mark.usefixtures("token_mode")
class TestPermissions:
    def test_roles_follow_the_same_rules_as_the_other_resources(self, client: TestClient) -> None:
        viewer = {"Authorization": "Bearer view-token-0001"}
        editor = {"Authorization": "Bearer edit-token-0002"}
        admin = {"Authorization": "Bearer admin-token-0003"}

        assert client.get("/projects", headers=viewer).status_code == 200
        assert client.post("/projects", json={"name": "A"}, headers=viewer).status_code == 403
        created = client.post("/projects", json={"name": "A"}, headers=editor)
        assert created.status_code == 201
        project_id = created.json()["id"]
        assert client.delete(f"/projects/{project_id}", headers=editor).status_code == 403
        assert client.delete(f"/projects/{project_id}", headers=admin).status_code == 204
