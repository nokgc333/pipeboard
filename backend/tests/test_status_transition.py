"""domain/status_transition.py の単体テスト。"""

from app.domain.status_transition import ALLOWED_STATUSES, is_valid_status


def test_all_defined_statuses_are_valid() -> None:
    for status in ["not_started", "in_progress", "in_review", "done"]:
        assert is_valid_status(status)


def test_unknown_status_is_invalid() -> None:
    assert is_valid_status("unknown") is False


def test_allowed_statuses_has_exactly_four_values() -> None:
    assert ALLOWED_STATUSES == frozenset({"not_started", "in_progress", "in_review", "done"})
