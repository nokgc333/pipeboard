"""houdini_status_update.py の単体テスト（TC-019〜022の自動化対象部分、仕様書§12.5）。

Houdini実機環境をCIに組み込むことは現実的でないため、HTTP呼び出しロジックのみを
hou非依存の関数として切り出し、requestsのレスポンスをモックして検証する。
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from houdini_status_update import build_status_update_url, send_status_update  # noqa: E402


def test_build_status_update_url_for_shot() -> None:
    url = build_status_update_url("http://localhost:8000", "shot", 12)

    assert url == "http://localhost:8000/shots/12/status"


def test_build_status_update_url_for_asset() -> None:
    url = build_status_update_url("http://localhost:8000", "asset", 5)

    assert url == "http://localhost:8000/assets/5/status"


def test_build_status_update_url_rejects_unknown_item_type() -> None:
    import pytest

    with pytest.raises(ValueError, match="item_type"):
        build_status_update_url("http://localhost:8000", "unknown", 1)


def test_send_status_update_calls_patch_with_expected_payload() -> None:
    session = MagicMock()
    session.patch.return_value.status_code = 200
    session.patch.return_value.json.return_value = {"id": 12, "status": "in_review"}

    result = send_status_update("http://localhost:8000", "shot", 12, "in_review", session=session)

    session.patch.assert_called_once_with(
        "http://localhost:8000/shots/12/status",
        json={"status": "in_review"},
        timeout=5,
    )
    assert result == {"id": 12, "status": "in_review"}


def test_send_status_update_raises_on_http_error() -> None:
    session = MagicMock()
    session.patch.return_value.status_code = 404
    session.patch.return_value.raise_for_status.side_effect = Exception("404 Not Found")

    import pytest

    with pytest.raises(Exception, match="404"):
        send_status_update("http://localhost:8000", "shot", 999, "done", session=session)


def test_send_status_update_sends_the_bearer_token_when_given() -> None:
    session = MagicMock()
    session.patch.return_value.json.return_value = {}

    send_status_update(
        "http://localhost:8000", "shot", 1, "done", session=session, token="secret-token-1"
    )

    session.patch.assert_called_once_with(
        "http://localhost:8000/shots/1/status",
        json={"status": "done"},
        timeout=5,
        headers={"Authorization": "Bearer secret-token-1"},
    )


def test_send_status_update_reads_the_token_from_the_environment(monkeypatch) -> None:
    monkeypatch.setenv("PIPEBOARD_API_TOKEN", "env-token-00001")
    session = MagicMock()
    session.patch.return_value.json.return_value = {}

    send_status_update("http://localhost:8000", "shot", 1, "done", session=session)

    assert session.patch.call_args.kwargs["headers"] == {"Authorization": "Bearer env-token-00001"}
