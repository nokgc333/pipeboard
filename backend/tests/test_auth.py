from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

TOKENS = "viewer=view-token-0001,editor=edit-token-0002,admin=admin-token-0003"


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def token_mode(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("PIPEBOARD_AUTH_MODE", "token")
    monkeypatch.setenv("PIPEBOARD_API_TOKENS", TOKENS)
    yield


class TestLocalMode:
    def test_requests_without_credentials_are_allowed_by_default(self, client: TestClient) -> None:
        assert client.get("/shots").status_code == 200
        assert client.post("/shots", json={"name": "SHOT010"}).status_code == 201

    def test_explicit_local_mode_is_the_same(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("PIPEBOARD_AUTH_MODE", "local")

        assert client.delete("/shots/1").status_code == 404


@pytest.mark.usefixtures("token_mode")
class TestAuthentication:
    def test_missing_token_is_rejected_with_401(self, client: TestClient) -> None:
        response = client.get("/shots")

        assert response.status_code == 401
        assert response.headers["www-authenticate"] == "Bearer"
        assert response.headers["content-type"] == "application/problem+json"

    def test_wrong_token_is_rejected_with_401(self, client: TestClient) -> None:
        assert client.get("/shots", headers=_bearer("nope-nope-nope")).status_code == 401

    def test_non_bearer_scheme_is_rejected_with_401(self, client: TestClient) -> None:
        response = client.get("/shots", headers={"Authorization": "Basic dXNlcjpwYXNz"})

        assert response.status_code == 401

    def test_healthz_stays_public(self, client: TestClient) -> None:
        assert client.get("/healthz").status_code == 200

    def test_a_valid_token_is_accepted(self, client: TestClient) -> None:
        assert client.get("/shots", headers=_bearer("view-token-0001")).status_code == 200

    def test_the_401_response_does_not_echo_the_submitted_token(self, client: TestClient) -> None:
        response = client.get("/shots", headers=_bearer("secret-guess-123"))

        assert "secret-guess-123" not in response.text


@pytest.mark.usefixtures("token_mode")
class TestAuthorization:
    def _create_shot(self, client: TestClient) -> int:
        response = client.post(
            "/shots", json={"name": "SHOT010"}, headers=_bearer("edit-token-0002")
        )
        return int(response.json()["id"])

    def test_viewer_can_read(self, client: TestClient) -> None:
        shot_id = self._create_shot(client)
        viewer = _bearer("view-token-0001")

        assert client.get("/shots", headers=viewer).status_code == 200
        assert client.get(f"/shots/{shot_id}", headers=viewer).status_code == 200
        assert client.get(f"/shots/{shot_id}/comments", headers=viewer).status_code == 200
        assert client.get(f"/shots/{shot_id}/versions", headers=viewer).status_code == 200

    def test_viewer_cannot_write(self, client: TestClient) -> None:
        shot_id = self._create_shot(client)
        viewer = _bearer("view-token-0001")

        assert client.post("/shots", json={"name": "X"}, headers=viewer).status_code == 403
        assert (
            client.put(f"/shots/{shot_id}", json={"name": "Y"}, headers=viewer).status_code == 403
        )
        assert (
            client.patch(
                f"/shots/{shot_id}/status", json={"status": "in_progress"}, headers=viewer
            ).status_code
            == 403
        )
        assert (
            client.post(
                "/comments",
                json={"item_type": "shot", "item_id": shot_id, "body": "hi"},
                headers=viewer,
            ).status_code
            == 403
        )

    def test_editor_can_write_but_not_delete(self, client: TestClient) -> None:
        shot_id = self._create_shot(client)
        editor = _bearer("edit-token-0002")

        assert (
            client.put(f"/shots/{shot_id}", json={"name": "Y"}, headers=editor).status_code == 200
        )
        assert (
            client.patch(
                f"/shots/{shot_id}/status", json={"status": "in_progress"}, headers=editor
            ).status_code
            == 200
        )
        assert client.delete(f"/shots/{shot_id}", headers=editor).status_code == 403

    def test_admin_can_delete(self, client: TestClient) -> None:
        shot_id = self._create_shot(client)

        response = client.delete(f"/shots/{shot_id}", headers=_bearer("admin-token-0003"))

        assert response.status_code == 204

    def test_asset_routes_follow_the_same_rules(self, client: TestClient) -> None:
        viewer = _bearer("view-token-0001")

        assert client.post("/assets", json={"name": "A"}, headers=viewer).status_code == 403
        assert client.delete("/assets/1", headers=_bearer("edit-token-0002")).status_code == 403

    def test_viewer_cannot_upload_a_version(self, client: TestClient) -> None:
        response = client.post(
            "/versions?item_type=shot&item_id=1",
            files={"file": ("a.png", b"x", "image/png")},
            headers=_bearer("view-token-0001"),
        )

        assert response.status_code == 403

    def test_forbidden_is_checked_before_the_resource_lookup(self, client: TestClient) -> None:
        response = client.delete("/shots/99999", headers=_bearer("view-token-0001"))

        assert response.status_code == 403


class TestAuthConfiguration:
    def test_token_mode_without_tokens_fails_loudly(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("PIPEBOARD_AUTH_MODE", "token")
        monkeypatch.delenv("PIPEBOARD_API_TOKENS", raising=False)

        with pytest.raises(ValueError, match="PIPEBOARD_API_TOKENS"):
            client.get("/shots")

    @pytest.mark.parametrize(
        "tokens",
        [
            "viewer=short",
            "boss=long-enough-token-1",
            "viewer",
            "viewer=a-long-token-0001,editor=a-long-token-0001",
        ],
    )
    def test_invalid_token_definitions_are_rejected(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch, tokens: str
    ) -> None:
        monkeypatch.setenv("PIPEBOARD_AUTH_MODE", "token")
        monkeypatch.setenv("PIPEBOARD_API_TOKENS", tokens)

        with pytest.raises(ValueError):
            client.get("/shots")

    def test_unknown_auth_mode_is_rejected(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("PIPEBOARD_AUTH_MODE", "oauth")

        with pytest.raises(ValueError, match="PIPEBOARD_AUTH_MODE"):
            client.get("/shots")
