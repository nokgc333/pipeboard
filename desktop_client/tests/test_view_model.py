"""view_model.py の単体テスト（DCC/PySide6非依存の純粋関数）。"""

from __future__ import annotations

from desktop_client.view_model import (
    STATUS_LABELS,
    STATUS_ORDER,
    group_shots_by_status,
    is_valid_status,
    status_label,
)


class TestStatusOrder:
    def test_status_order_matches_frontend_domain(self) -> None:
        assert STATUS_ORDER == ("not_started", "in_progress", "in_review", "done")

    def test_status_labels_cover_all_statuses(self) -> None:
        assert set(STATUS_LABELS) == set(STATUS_ORDER)

    def test_status_labels_are_japanese(self) -> None:
        assert STATUS_LABELS["not_started"] == "未着手"
        assert STATUS_LABELS["in_progress"] == "作業中"
        assert STATUS_LABELS["in_review"] == "レビュー"
        assert STATUS_LABELS["done"] == "完了"


class TestIsValidStatus:
    def test_known_status_is_valid(self) -> None:
        assert is_valid_status("in_progress") is True

    def test_unknown_status_is_invalid(self) -> None:
        assert is_valid_status("archived") is False


class TestStatusLabel:
    def test_returns_japanese_label_for_known_status(self) -> None:
        assert status_label("done") == "完了"

    def test_falls_back_to_raw_value_for_unknown_status(self) -> None:
        assert status_label("archived") == "archived"


class TestGroupShotsByStatus:
    def test_groups_shots_into_matching_status_bucket(self) -> None:
        shots = [
            {"id": 1, "name": "SHOT010", "status": "not_started"},
            {"id": 2, "name": "SHOT020", "status": "in_progress"},
        ]

        grouped = group_shots_by_status(shots)

        assert grouped["not_started"] == [shots[0]]
        assert grouped["in_progress"] == [shots[1]]

    def test_returns_all_status_keys_even_when_empty(self) -> None:
        grouped = group_shots_by_status([])

        assert set(grouped.keys()) == set(STATUS_ORDER)
        assert all(bucket == [] for bucket in grouped.values())

    def test_multiple_shots_in_same_status_preserve_insertion_order(self) -> None:
        shots = [
            {"id": 1, "name": "A", "status": "done"},
            {"id": 2, "name": "B", "status": "done"},
        ]

        grouped = group_shots_by_status(shots)

        assert [s["id"] for s in grouped["done"]] == [1, 2]

    def test_unknown_status_shot_is_excluded_from_all_buckets(self) -> None:
        shots = [{"id": 1, "name": "X", "status": "archived"}]

        grouped = group_shots_by_status(shots)

        assert all(shot["id"] != 1 for bucket in grouped.values() for shot in bucket)

    def test_keys_are_returned_in_status_order(self) -> None:
        grouped = group_shots_by_status([])

        assert list(grouped.keys()) == list(STATUS_ORDER)
