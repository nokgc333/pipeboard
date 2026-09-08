"""api_client.py の単体テスト。

requestsのみを直接呼び出さず、注入可能な`session`（FakeSession）でネットワークなしに
HTTP呼び出しロジックを検証する（houdini_status_update.pyと同じ思想）。
"""

from __future__ import annotations

from typing import Any

import pytest

from desktop_client.api_client import ApiError, PipeBoardApiClient


class FakeResponse:
    def __init__(self, status_code: int, json_data: Any = None) -> None:
        self.status_code = status_code
        self._json_data = json_data if json_data is not None else {}

    def json(self) -> Any:
        return self._json_data


class BrokenJsonResponse(FakeResponse):
    def json(self) -> Any:
        raise ValueError("response body is not JSON")


class FakeSession:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict[str, Any]]] = []
        self.get_response: FakeResponse = FakeResponse(200, [])
        self.post_response: FakeResponse = FakeResponse(201, {})
        self.patch_response: FakeResponse = FakeResponse(200, {})

    def get(self, url: str, **kwargs: Any) -> FakeResponse:
        self.calls.append(("GET", url, kwargs))
        return self.get_response

    def post(self, url: str, **kwargs: Any) -> FakeResponse:
        self.calls.append(("POST", url, kwargs))
        return self.post_response

    def patch(self, url: str, **kwargs: Any) -> FakeResponse:
        self.calls.append(("PATCH", url, kwargs))
        return self.patch_response


class TestListShots:
    def test_list_shots_calls_get_shots_endpoint(self) -> None:
        session = FakeSession()
        session.get_response = FakeResponse(
            200, [{"id": 1, "name": "SHOT010", "status": "not_started"}]
        )
        client = PipeBoardApiClient("http://localhost:8000", session=session)

        shots = client.list_shots()

        assert shots == [{"id": 1, "name": "SHOT010", "status": "not_started"}]
        method, url, _ = session.calls[0]
        assert (method, url) == ("GET", "http://localhost:8000/shots")


class TestListAssets:
    def test_list_assets_calls_get_assets_endpoint(self) -> None:
        session = FakeSession()
        session.get_response = FakeResponse(
            200, [{"id": 2, "name": "Prop_Chair", "status": "done"}]
        )
        client = PipeBoardApiClient("http://localhost:8000", session=session)

        assets = client.list_assets()

        assert assets[0]["name"] == "Prop_Chair"
        assert session.calls[0][1] == "http://localhost:8000/assets"


class TestUpdateShotStatus:
    def test_update_shot_status_calls_patch_shots_status_endpoint(self) -> None:
        session = FakeSession()
        session.patch_response = FakeResponse(200, {"id": 1, "status": "in_review"})
        client = PipeBoardApiClient("http://localhost:8000", session=session)

        result = client.update_shot_status(1, "in_review")

        assert result["status"] == "in_review"
        method, url, kwargs = session.calls[0]
        assert method == "PATCH"
        assert url == "http://localhost:8000/shots/1/status"
        assert kwargs["json"] == {"status": "in_review"}


class TestUpdateItemStatus:
    def test_update_item_status_for_shot(self) -> None:
        session = FakeSession()
        client = PipeBoardApiClient("http://localhost:8000", session=session)

        client.update_item_status("shot", 1, "done")

        assert session.calls[0][1] == "http://localhost:8000/shots/1/status"

    def test_update_item_status_for_asset(self) -> None:
        session = FakeSession()
        client = PipeBoardApiClient("http://localhost:8000", session=session)

        client.update_item_status("asset", 5, "done")

        assert session.calls[0][1] == "http://localhost:8000/assets/5/status"

    def test_update_item_status_rejects_unknown_item_type(self) -> None:
        client = PipeBoardApiClient("http://localhost:8000", session=FakeSession())

        with pytest.raises(ValueError, match="item_type"):
            client.update_item_status("unknown", 1, "done")


class TestListVersions:
    def test_list_versions_for_shot(self) -> None:
        session = FakeSession()
        session.get_response = FakeResponse(200, [{"id": 1, "version_number": 2}])
        client = PipeBoardApiClient("http://localhost:8000", session=session)

        versions = client.list_versions("shot", 1)

        assert versions[0]["version_number"] == 2
        assert session.calls[0][1] == "http://localhost:8000/shots/1/versions"

    def test_list_versions_for_asset(self) -> None:
        session = FakeSession()
        client = PipeBoardApiClient("http://localhost:8000", session=session)

        client.list_versions("asset", 3)

        assert session.calls[0][1] == "http://localhost:8000/assets/3/versions"

    def test_list_versions_rejects_unknown_item_type(self) -> None:
        client = PipeBoardApiClient("http://localhost:8000", session=FakeSession())

        with pytest.raises(ValueError, match="item_type"):
            client.list_versions("unknown", 1)


class TestListComments:
    def test_list_comments_for_shot(self) -> None:
        session = FakeSession()
        session.get_response = FakeResponse(200, [{"id": 1, "body": "hi"}])
        client = PipeBoardApiClient("http://localhost:8000", session=session)

        comments = client.list_comments("shot", 1)

        assert comments[0]["body"] == "hi"
        assert session.calls[0][1] == "http://localhost:8000/shots/1/comments"

    def test_list_comments_for_asset(self) -> None:
        session = FakeSession()
        client = PipeBoardApiClient("http://localhost:8000", session=session)

        client.list_comments("asset", 7)

        assert session.calls[0][1] == "http://localhost:8000/assets/7/comments"


class TestCreateComment:
    def test_create_comment_posts_to_comments_endpoint(self) -> None:
        session = FakeSession()
        session.post_response = FakeResponse(201, {"id": 1, "body": "note", "tag": None})
        client = PipeBoardApiClient("http://localhost:8000", session=session)

        result = client.create_comment("shot", 1, "note")

        assert result["body"] == "note"
        method, url, kwargs = session.calls[0]
        assert method == "POST"
        assert url == "http://localhost:8000/comments"
        assert kwargs["json"] == {"item_type": "shot", "item_id": 1, "body": "note", "tag": None}

    def test_create_comment_with_tag(self) -> None:
        session = FakeSession()
        client = PipeBoardApiClient("http://localhost:8000", session=session)

        client.create_comment("shot", 1, "note", tag="risk")

        assert session.calls[0][2]["json"]["tag"] == "risk"


class TestErrorHandling:
    def test_raises_api_error_on_4xx_with_problem_details_title(self) -> None:
        session = FakeSession()
        session.get_response = FakeResponse(404, {"title": "Shot 999 not found", "status": 404})
        client = PipeBoardApiClient("http://localhost:8000", session=session)

        with pytest.raises(ApiError) as exc_info:
            client.list_versions("shot", 999)

        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.title

    def test_raises_api_error_with_fallback_title_when_body_not_json(self) -> None:
        session = FakeSession()
        session.get_response = BrokenJsonResponse(500)
        client = PipeBoardApiClient("http://localhost:8000", session=session)

        with pytest.raises(ApiError) as exc_info:
            client.list_shots()

        assert exc_info.value.status_code == 500
        assert "500" in exc_info.value.title

    def test_api_error_str_includes_status_and_title(self) -> None:
        error = ApiError(404, "Shot 1 not found")

        assert "404" in str(error)
        assert "Shot 1 not found" in str(error)


class TestClientConstruction:
    def test_base_url_trailing_slash_is_normalized(self) -> None:
        session = FakeSession()
        client = PipeBoardApiClient("http://localhost:8000/", session=session)

        client.list_shots()

        assert session.calls[0][1] == "http://localhost:8000/shots"

    def test_default_session_is_requests_session_when_not_injected(self) -> None:
        import requests

        client = PipeBoardApiClient("http://localhost:8000")

        assert isinstance(client._session, requests.Session)
