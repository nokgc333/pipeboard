"""公開ゲート(検査に通っていないものは、レビュー・完了に進めない)の純粋な判定のテスト。"""

from __future__ import annotations

import pytest

from app.domain.publish_gate import GATED_STATUSES, CheckSummary, evaluate_gate


def _check(tool: str, passed: bool) -> CheckSummary:
    return CheckSummary(tool=tool, passed=passed)


def test_with_no_required_tools_every_transition_is_allowed() -> None:
    decision = evaluate_gate("done", required_tools=(), latest_checks={})

    assert decision.allowed
    assert decision.reason is None


@pytest.mark.parametrize("target", ["not_started", "in_progress"])
def test_statuses_before_review_are_never_gated(target: str) -> None:
    decision = evaluate_gate(target, required_tools=("scene-doctor",), latest_checks={})

    assert decision.allowed


@pytest.mark.parametrize("target", ["in_review", "done"])
def test_review_and_done_are_gated(target: str) -> None:
    decision = evaluate_gate(target, required_tools=("scene-doctor",), latest_checks={})

    assert not decision.allowed
    assert target in GATED_STATUSES


def test_a_missing_check_is_reported_by_tool_name() -> None:
    decision = evaluate_gate("done", ("scene-doctor", "unibridge"), {})

    assert decision.reason == "Missing checks: scene-doctor, unibridge"


def test_a_failed_check_is_reported_separately_from_a_missing_one() -> None:
    decision = evaluate_gate(
        "in_review",
        ("scene-doctor", "unibridge"),
        {"scene-doctor": _check("scene-doctor", False)},
    )

    assert decision.reason == "Failed checks: scene-doctor; Missing checks: unibridge"


def test_all_required_checks_passing_allows_the_transition() -> None:
    decision = evaluate_gate(
        "done",
        ("scene-doctor", "unibridge"),
        {"scene-doctor": _check("scene-doctor", True), "unibridge": _check("unibridge", True)},
    )

    assert decision.allowed


def test_a_check_from_a_tool_that_is_not_required_is_ignored() -> None:
    decision = evaluate_gate("done", ("scene-doctor",), {"other": _check("other", True)})

    assert not decision.allowed
    assert decision.reason == "Missing checks: scene-doctor"


def test_extra_passing_checks_do_not_matter_when_the_required_ones_pass() -> None:
    decision = evaluate_gate(
        "done",
        ("scene-doctor",),
        {"scene-doctor": _check("scene-doctor", True), "other": _check("other", False)},
    )

    assert decision.allowed


def test_several_failed_checks_are_listed_in_the_order_they_are_required() -> None:
    decision = evaluate_gate(
        "done",
        ("scene-doctor", "unibridge"),
        {"unibridge": _check("unibridge", False), "scene-doctor": _check("scene-doctor", False)},
    )

    assert decision.reason == "Failed checks: scene-doctor, unibridge"


def test_a_blocked_decision_is_exactly_false_and_an_allowed_one_exactly_true() -> None:
    blocked = evaluate_gate("done", ("scene-doctor",), {})
    allowed = evaluate_gate("done", (), {})

    assert blocked.allowed is False
    assert allowed.allowed is True
