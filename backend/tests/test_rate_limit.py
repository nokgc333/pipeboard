import pytest
from fastapi.testclient import TestClient

from app import rate_limit


@pytest.fixture(autouse=True)
def fresh_limiter() -> None:
    rate_limit.reset()


class TestRateLimit:
    def test_reads_over_the_limit_get_429(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("PIPEBOARD_RATE_LIMIT_READ_PER_MINUTE", "3")

        statuses = [client.get("/shots").status_code for _ in range(5)]

        assert statuses == [200, 200, 200, 429, 429]

    def test_the_429_response_tells_when_to_retry(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("PIPEBOARD_RATE_LIMIT_READ_PER_MINUTE", "1")
        client.get("/shots")

        response = client.get("/shots")

        assert response.status_code == 429
        assert int(response.headers["retry-after"]) >= 1
        assert response.headers["content-type"] == "application/problem+json"

    def test_writes_have_their_own_stricter_budget(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("PIPEBOARD_RATE_LIMIT_WRITE_PER_MINUTE", "2")

        statuses = [client.post("/shots", json={"name": f"S{i}"}).status_code for i in range(4)]
        read_status = client.get("/shots").status_code

        assert statuses == [201, 201, 429, 429]
        assert read_status == 200

    def test_clients_are_counted_separately(self) -> None:
        limiter = rate_limit.SlidingWindowLimiter()

        assert limiter.check("10.0.0.1:read", limit=1, now=0.0) == 0
        assert limiter.check("10.0.0.2:read", limit=1, now=0.0) == 0
        assert limiter.check("10.0.0.1:read", limit=1, now=1.0) > 0

    def test_window_expiry_frees_the_budget(self, monkeypatch: pytest.MonkeyPatch) -> None:
        limiter = rate_limit.SlidingWindowLimiter()

        assert limiter.check("k", limit=1, now=0.0) == 0
        assert limiter.check("k", limit=1, now=10.0) > 0
        assert limiter.check("k", limit=1, now=61.0) == 0

    def test_healthz_is_not_limited(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("PIPEBOARD_RATE_LIMIT_READ_PER_MINUTE", "1")

        assert [client.get("/healthz").status_code for _ in range(3)] == [200, 200, 200]

    @pytest.mark.parametrize("value", ["0", "-1", "many"])
    def test_invalid_limit_values_are_rejected(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch, value: str
    ) -> None:
        monkeypatch.setenv("PIPEBOARD_RATE_LIMIT_READ_PER_MINUTE", value)

        with pytest.raises(ValueError, match="PIPEBOARD_RATE_LIMIT_READ_PER_MINUTE"):
            client.get("/shots")
