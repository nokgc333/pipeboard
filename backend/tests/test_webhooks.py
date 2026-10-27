"""変更の Webhook 通知のテスト。"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app import webhooks

URL = "https://hooks.example.test/pipeboard"
SECRET = "0123456789abcdef-secret"

Call = tuple[str, bytes, dict[str, str]]


@pytest.fixture()
def sent() -> Iterator[list[Call]]:
    calls: list[Call] = []
    webhooks.set_sender(lambda url, body, headers: calls.append((url, body, headers)))
    yield calls
    webhooks.reset_sender()


@pytest.fixture()
def configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PIPEBOARD_WEBHOOK_URL", URL)
    monkeypatch.setenv("PIPEBOARD_WEBHOOK_SECRET", SECRET)


@pytest.mark.usefixtures("configured")
class TestDelivery:
    def test_a_committed_change_is_posted_to_the_url(
        self, client: TestClient, sent: list[Call]
    ) -> None:
        client.post("/shots", json={"name": "SHOT010"})
        webhooks.flush()

        assert len(sent) == 1
        url, body, headers = sent[0]
        event = json.loads(body)
        assert url == URL
        assert event["action"] == "shot.create"
        assert event["item_type"] == "shot"
        assert event["detail"] == {"name": "SHOT010"}
        assert headers["X-PipeBoard-Event"] == "shot.create"

    def test_the_body_is_signed_with_the_shared_secret(
        self, client: TestClient, sent: list[Call]
    ) -> None:
        client.post("/shots", json={"name": "SHOT010"})
        webhooks.flush()

        _, body, headers = sent[0]
        expected = "sha256=" + hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()
        assert headers["X-PipeBoard-Signature"] == expected

    def test_a_different_secret_gives_a_different_signature(self) -> None:
        assert webhooks.sign("a" * 16, b"x") != webhooks.sign("b" * 16, b"x")

    def test_each_kind_of_change_sends_its_own_event(
        self, client: TestClient, sent: list[Call]
    ) -> None:
        shot_id = client.post("/shots", json={"name": "SHOT010"}).json()["id"]
        client.patch(f"/shots/{shot_id}/status", json={"status": "done"})
        client.post("/comments", json={"item_type": "shot", "item_id": shot_id, "body": "ok"})
        webhooks.flush()

        assert [h["X-PipeBoard-Event"] for _, _, h in sent] == [
            "shot.create",
            "shot.status",
            "comment.create",
        ]

    def test_a_rejected_request_sends_nothing(self, client: TestClient, sent: list[Call]) -> None:
        client.patch("/shots/9999/status", json={"status": "done"})
        client.post("/shots", json={"name": ""})
        webhooks.flush()

        assert sent == []

    def test_reads_send_nothing(self, client: TestClient, sent: list[Call]) -> None:
        client.get("/shots")
        webhooks.flush()

        assert sent == []

    def test_a_failing_endpoint_does_not_fail_the_request_and_is_logged(
        self, client: TestClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        def broken(url: str, body: bytes, headers: dict[str, str]) -> None:
            raise OSError("connection refused")

        webhooks.set_sender(broken)
        try:
            with caplog.at_level(logging.WARNING, logger="pipeboard.webhooks"):
                response = client.post("/shots", json={"name": "SHOT010"})
                webhooks.flush()
        finally:
            webhooks.reset_sender()

        assert response.status_code == 201
        assert "webhook delivery failed for shot.create" in caplog.text


def test_without_a_url_nothing_is_sent(client: TestClient, sent: list[Call]) -> None:
    client.post("/shots", json={"name": "SHOT010"})
    webhooks.flush()

    assert sent == []


class TestSettings:
    def test_unset_means_disabled(self) -> None:
        assert webhooks.load_webhook_settings() == webhooks.WebhookSettings(None, None)

    @pytest.mark.parametrize("url", ["ftp://x.test/h", "not a url", "https://"])
    def test_only_http_and_https_urls_are_accepted(
        self, monkeypatch: pytest.MonkeyPatch, url: str
    ) -> None:
        monkeypatch.setenv("PIPEBOARD_WEBHOOK_URL", url)
        monkeypatch.setenv("PIPEBOARD_WEBHOOK_SECRET", SECRET)

        with pytest.raises(ValueError, match="http or https"):
            webhooks.load_webhook_settings()

    def test_a_url_requires_a_long_enough_secret(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PIPEBOARD_WEBHOOK_URL", URL)
        monkeypatch.setenv("PIPEBOARD_WEBHOOK_SECRET", "short")

        with pytest.raises(ValueError, match="at least 16"):
            webhooks.load_webhook_settings()

    def test_a_url_without_a_secret_is_refused(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PIPEBOARD_WEBHOOK_URL", URL)

        with pytest.raises(ValueError, match="PIPEBOARD_WEBHOOK_SECRET"):
            webhooks.load_webhook_settings()

    def test_a_bad_setting_stops_the_application_at_startup(
        self, db_session_factory, monkeypatch: pytest.MonkeyPatch  # type: ignore[no-untyped-def]
    ) -> None:
        from app.main import app

        monkeypatch.setenv("PIPEBOARD_WEBHOOK_URL", "ftp://x.test/h")
        monkeypatch.setenv("PIPEBOARD_WEBHOOK_SECRET", SECRET)

        with pytest.raises(ValueError):
            with TestClient(app):
                pass
