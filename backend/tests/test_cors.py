import pytest
from fastapi.testclient import TestClient

from app import cors


def _preflight(client: TestClient, origin: str):
    return client.options(
        "/shots",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )


class TestAllowedOrigins:
    def test_default_is_the_local_frontend_only(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("PIPEBOARD_CORS_ORIGINS", raising=False)

        assert cors.load_allowed_origins() == ["http://localhost:3000"]

    def test_several_origins_can_be_listed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PIPEBOARD_CORS_ORIGINS", "https://a.example, https://b.example")

        assert cors.load_allowed_origins() == ["https://a.example", "https://b.example"]

    def test_wildcard_is_only_used_when_set_explicitly(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("PIPEBOARD_CORS_ORIGINS", "*")

        assert cors.load_allowed_origins() == ["*"]

    def test_wildcard_mixed_with_other_origins_is_rejected(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("PIPEBOARD_CORS_ORIGINS", "*,https://a.example")

        with pytest.raises(ValueError, match="PIPEBOARD_CORS_ORIGINS"):
            cors.load_allowed_origins()


class TestPreflight:
    def test_the_default_origin_is_allowed(self, client: TestClient) -> None:
        response = _preflight(client, "http://localhost:3000")

        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
        assert "authorization" in response.headers["access-control-allow-headers"].lower()

    def test_another_origin_is_not_allowed_by_default(self, client: TestClient) -> None:
        response = _preflight(client, "https://evil.example")

        assert "access-control-allow-origin" not in response.headers

    def test_credentials_are_never_allowed(self, client: TestClient) -> None:
        response = _preflight(client, "http://localhost:3000")

        assert "access-control-allow-credentials" not in response.headers
