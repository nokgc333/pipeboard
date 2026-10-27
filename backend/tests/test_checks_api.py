"""検査結果の提出と、公開ゲート(未通過はレビュー・完了に進めない)の API テスト。"""

from __future__ import annotations

import json
from typing import Any

import pytest
from fastapi.testclient import TestClient

TOKENS = "viewer=view-token-0001,editor=edit-token-0002,admin=admin-token-0003"


def _report(
    tool: str = "scene-doctor",
    has_errors: bool = False,
    findings: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": "1",
        "tool": tool,
        "generated_at": "2026-10-27T01:02:03+00:00",
        "subject": "scene.hip",
        "has_errors": has_errors,
        "findings": findings or [],
    }


def _finding(severity: str) -> dict[str, str]:
    return {"rule": "naming", "severity": severity, "target": "/a", "message": "m"}


def _new_shot(client: TestClient) -> int:
    return int(client.post("/shots", json={"name": "SHOT010"}).json()["id"])


class TestSubmitting:
    def test_a_passing_report_is_stored_as_passed(self, client: TestClient) -> None:
        shot_id = _new_shot(client)

        response = client.post(f"/shots/{shot_id}/checks", json=_report())

        assert response.status_code == 201
        body = response.json()
        assert body["passed"] is True
        assert body["tool"] == "scene-doctor"
        assert body["item_type"] == "shot"
        assert body["item_id"] == shot_id

    def test_a_report_with_errors_is_stored_as_failed_with_counts(self, client: TestClient) -> None:
        shot_id = _new_shot(client)
        findings = [_finding("error"), _finding("error"), _finding("warning"), _finding("info")]

        body = client.post(
            f"/shots/{shot_id}/checks", json=_report(has_errors=True, findings=findings)
        ).json()

        assert body["passed"] is False
        assert (body["error_count"], body["warning_count"]) == (2, 1)

    def test_the_history_is_listed_newest_first(self, client: TestClient) -> None:
        shot_id = _new_shot(client)
        client.post(f"/shots/{shot_id}/checks", json=_report(has_errors=True))
        client.post(f"/shots/{shot_id}/checks", json=_report())

        history = client.get(f"/shots/{shot_id}/checks").json()

        assert [c["passed"] for c in history] == [True, False]

    def test_assets_accept_checks_too(self, client: TestClient) -> None:
        asset_id = client.post("/assets", json={"name": "Prop"}).json()["id"]

        response = client.post(f"/assets/{asset_id}/checks", json=_report("unibridge"))

        assert response.status_code == 201
        assert response.json()["item_type"] == "asset"

    def test_a_missing_item_gives_404(self, client: TestClient) -> None:
        assert client.post("/shots/9999/checks", json=_report()).status_code == 404

    @pytest.mark.parametrize(
        "change",
        [
            {"schema_version": "2"},
            {"tool": "Scene Doctor"},
            {"tool": ""},
            {"has_errors": "yes"},
            {"findings": [{"rule": "r", "severity": "fatal", "target": "t", "message": "m"}]},
            {"findings": [{"rule": "r", "severity": "error", "target": "t"}]},
            {"extra": 1},
        ],
    )
    def test_a_report_that_does_not_follow_the_shared_format_is_rejected(
        self, client: TestClient, change: dict[str, Any]
    ) -> None:
        shot_id = _new_shot(client)

        response = client.post(f"/shots/{shot_id}/checks", json={**_report(), **change})

        assert response.status_code == 422

    def test_too_many_findings_are_rejected(self, client: TestClient) -> None:
        shot_id = _new_shot(client)
        report = _report(findings=[_finding("info")] * 2001)

        assert client.post(f"/shots/{shot_id}/checks", json=report).status_code == 422

    def test_submitting_is_recorded_in_the_audit_log(self, client: TestClient) -> None:
        shot_id = _new_shot(client)
        client.post(f"/shots/{shot_id}/checks", json=_report())

        entry = client.get("/audit-log").json()[0]

        assert entry["action"] == "shot.check"
        assert json.loads(entry["detail"])["tool"] == "scene-doctor"

    def test_deleting_the_item_removes_its_checks(self, client: TestClient) -> None:
        shot_id = _new_shot(client)
        client.post(f"/shots/{shot_id}/checks", json=_report())
        client.delete(f"/shots/{shot_id}")

        assert client.get(f"/shots/{shot_id}/checks").status_code == 404


class TestGate:
    @pytest.fixture(autouse=True)
    def required(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PIPEBOARD_REQUIRED_CHECKS", "scene-doctor,unibridge")

    def test_review_is_blocked_without_checks(self, client: TestClient) -> None:
        shot_id = _new_shot(client)

        response = client.patch(f"/shots/{shot_id}/status", json={"status": "in_review"})

        assert response.status_code == 409
        assert response.json()["title"] == "Missing checks: scene-doctor, unibridge"

    def test_earlier_statuses_are_not_blocked(self, client: TestClient) -> None:
        shot_id = _new_shot(client)

        assert (
            client.patch(f"/shots/{shot_id}/status", json={"status": "in_progress"}).status_code
            == 200
        )

    def test_a_failed_check_blocks_done(self, client: TestClient) -> None:
        shot_id = _new_shot(client)
        client.post(f"/shots/{shot_id}/checks", json=_report("scene-doctor", has_errors=True))
        client.post(f"/shots/{shot_id}/checks", json=_report("unibridge"))

        response = client.patch(f"/shots/{shot_id}/status", json={"status": "done"})

        assert response.status_code == 409
        assert response.json()["title"] == "Failed checks: scene-doctor"

    def test_all_required_checks_passing_lets_the_item_through(self, client: TestClient) -> None:
        shot_id = _new_shot(client)
        client.post(f"/shots/{shot_id}/checks", json=_report("scene-doctor"))
        client.post(f"/shots/{shot_id}/checks", json=_report("unibridge"))

        response = client.patch(f"/shots/{shot_id}/status", json={"status": "done"})

        assert response.status_code == 200
        assert response.json()["status"] == "done"

    def test_only_the_latest_result_of_a_tool_counts(self, client: TestClient) -> None:
        shot_id = _new_shot(client)
        client.post(f"/shots/{shot_id}/checks", json=_report("scene-doctor"))
        client.post(f"/shots/{shot_id}/checks", json=_report("unibridge"))
        client.post(f"/shots/{shot_id}/checks", json=_report("scene-doctor", has_errors=True))

        assert client.patch(f"/shots/{shot_id}/status", json={"status": "done"}).status_code == 409

        client.post(f"/shots/{shot_id}/checks", json=_report("scene-doctor"))

        assert client.patch(f"/shots/{shot_id}/status", json={"status": "done"}).status_code == 200

    def test_checks_of_another_item_do_not_count(self, client: TestClient) -> None:
        first = _new_shot(client)
        second = _new_shot(client)
        client.post(f"/shots/{first}/checks", json=_report("scene-doctor"))
        client.post(f"/shots/{first}/checks", json=_report("unibridge"))

        assert client.patch(f"/shots/{second}/status", json={"status": "done"}).status_code == 409

    def test_a_shot_check_does_not_pass_an_asset_with_the_same_id(self, client: TestClient) -> None:
        shot_id = _new_shot(client)
        asset_id = client.post("/assets", json={"name": "Prop"}).json()["id"]
        assert shot_id == asset_id
        client.post(f"/shots/{shot_id}/checks", json=_report("scene-doctor"))
        client.post(f"/shots/{shot_id}/checks", json=_report("unibridge"))

        assert (
            client.patch(f"/assets/{asset_id}/status", json={"status": "done"}).status_code == 409
        )

    def test_a_blocked_change_leaves_the_status_and_the_log_untouched(
        self, client: TestClient
    ) -> None:
        shot_id = _new_shot(client)
        before = len(client.get("/audit-log").json())

        client.patch(f"/shots/{shot_id}/status", json={"status": "done"})

        assert client.get(f"/shots/{shot_id}").json()["status"] == "not_started"
        assert len(client.get("/audit-log").json()) == before


def test_without_the_setting_the_gate_is_off(client: TestClient) -> None:
    shot_id = _new_shot(client)

    assert client.patch(f"/shots/{shot_id}/status", json={"status": "done"}).status_code == 200


def test_an_invalid_tool_name_in_the_setting_stops_startup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.gate_settings import load_required_checks

    monkeypatch.setenv("PIPEBOARD_REQUIRED_CHECKS", "scene-doctor,Bad Name")

    with pytest.raises(ValueError, match="Bad Name"):
        load_required_checks()


def test_the_setting_ignores_blanks_and_duplicates(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.gate_settings import load_required_checks

    monkeypatch.setenv("PIPEBOARD_REQUIRED_CHECKS", " scene-doctor , ,unibridge,scene-doctor")

    assert load_required_checks() == ("scene-doctor", "unibridge")


@pytest.fixture()
def token_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PIPEBOARD_AUTH_MODE", "token")
    monkeypatch.setenv("PIPEBOARD_API_TOKENS", TOKENS)


@pytest.mark.usefixtures("token_mode")
class TestPermissions:
    def test_a_viewer_cannot_submit_but_can_read(self, client: TestClient) -> None:
        editor = {"Authorization": "Bearer edit-token-0002"}
        viewer = {"Authorization": "Bearer view-token-0001"}
        shot_id = client.post("/shots", json={"name": "S"}, headers=editor).json()["id"]

        assert (
            client.post(f"/shots/{shot_id}/checks", json=_report(), headers=viewer).status_code
            == 403
        )
        assert (
            client.post(f"/shots/{shot_id}/checks", json=_report(), headers=editor).status_code
            == 201
        )
        assert client.get(f"/shots/{shot_id}/checks", headers=viewer).status_code == 200
