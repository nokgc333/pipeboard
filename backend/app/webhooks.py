"""変更の Webhook 通知。コミットが成功したあとに、別スレッドで送る(失敗しても要求は失敗させない)。"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import urllib.request
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger("pipeboard.webhooks")

SIGNATURE_HEADER = "X-PipeBoard-Signature"
EVENT_HEADER = "X-PipeBoard-Event"
TIMEOUT_SECONDS = 5
MIN_SECRET_LENGTH = 16


@dataclass(frozen=True)
class WebhookSettings:
    url: str | None
    secret: str | None


def load_webhook_settings() -> WebhookSettings:
    url = os.environ.get("PIPEBOARD_WEBHOOK_URL") or None
    secret = os.environ.get("PIPEBOARD_WEBHOOK_SECRET") or None
    if url is None:
        return WebhookSettings(url=None, secret=None)
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("PIPEBOARD_WEBHOOK_URL must be an http or https URL")
    if secret is None or len(secret) < MIN_SECRET_LENGTH:
        raise ValueError(
            f"PIPEBOARD_WEBHOOK_SECRET must be at least {MIN_SECRET_LENGTH} characters "
            "when PIPEBOARD_WEBHOOK_URL is set"
        )
    return WebhookSettings(url=url, secret=secret)


def sign(secret: str, body: bytes) -> str:
    return "sha256=" + hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


Sender = Callable[[str, bytes, dict[str, str]], None]


def _http_post(url: str, body: bytes, headers: dict[str, str]) -> None:
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS):  # noqa: S310
        pass


_sender: Sender = _http_post
_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="pipeboard-webhook")
_pending: list[Future[None]] = []


def set_sender(sender: Sender) -> None:
    global _sender
    _sender = sender


def reset_sender() -> None:
    set_sender(_http_post)


def _deliver(settings: WebhookSettings, event: dict[str, Any]) -> None:
    assert settings.url is not None and settings.secret is not None
    body = json.dumps(event, ensure_ascii=False, sort_keys=True).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        EVENT_HEADER: str(event["action"]),
        SIGNATURE_HEADER: sign(settings.secret, body),
    }
    try:
        _sender(settings.url, body, headers)
    except Exception:  # noqa: BLE001 - 通知の失敗で、本体の処理を止めない
        logger.warning("webhook delivery failed for %s", event["action"], exc_info=True)


def notify(event: dict[str, Any]) -> None:
    settings = load_webhook_settings()
    if settings.url is None:
        return
    _pending.append(_executor.submit(_deliver, settings, event))


def flush() -> None:
    while _pending:
        _pending.pop().result()
