"""main_window.py の単体テスト（本物のPySide6ウィジェット + pytest-qtのqtbotで検証）。

`QT_QPA_PLATFORM=offscreen`（tests/conftest.py）によりヘッドレス環境で実ウィジェットを
生成・操作する。fakeのapi_clientを注入することで実HTTP通信なしに検証する
（scene_doctor/tests/test_panel.pyと同じ手法）。
"""

from __future__ import annotations

from typing import Any

from pytestqt.qtbot import QtBot

from desktop_client.api_client import ApiError
from desktop_client.main_window import PipeBoardMainWindow


class FakeApiClient:
    def __init__(
        self,
        shots: list[dict[str, Any]] | None = None,
        raise_on_list: Exception | None = None,
    ) -> None:
        self._shots = shots if shots is not None else []
        self._raise_on_list = raise_on_list
        self.update_calls: list[tuple[int, str]] = []

    def list_shots(self) -> list[dict[str, Any]]:
        if self._raise_on_list is not None:
            raise self._raise_on_list
        return self._shots

    def update_shot_status(self, shot_id: int, status: str) -> dict[str, Any]:
        self.update_calls.append((shot_id, status))
        for shot in self._shots:
            if shot["id"] == shot_id:
                shot["status"] = status
        return {"id": shot_id, "status": status}


def _sample_shots() -> list[dict[str, Any]]:
    return [
        {"id": 1, "name": "SHOT010", "status": "not_started"},
        {"id": 2, "name": "SHOT020", "status": "in_progress"},
        {"id": 3, "name": "SHOT030", "status": "done"},
    ]


def _make_window(qtbot: QtBot, api_client: FakeApiClient | None = None) -> PipeBoardMainWindow:
    window = PipeBoardMainWindow(api_client=api_client or FakeApiClient())
    qtbot.addWidget(window)
    window.show()
    return window


class TestConstruction:
    def test_window_constructs_with_empty_lists(self, qtbot: QtBot) -> None:
        window = _make_window(qtbot)

        assert all(lw.count() == 0 for lw in window.status_lists.values())

    def test_window_has_one_list_per_status(self, qtbot: QtBot) -> None:
        window = _make_window(qtbot)

        assert set(window.status_lists.keys()) == {
            "not_started",
            "in_progress",
            "in_review",
            "done",
        }

    def test_status_label_shows_zero_initially(self, qtbot: QtBot) -> None:
        window = _make_window(qtbot)

        assert "0" in window.status_label.text()


class TestReload:
    def test_reload_button_click_invokes_list_shots(self, qtbot: QtBot) -> None:
        fake = FakeApiClient(shots=_sample_shots())
        window = _make_window(qtbot, fake)

        window.reload_button.click()

        assert window.status_lists["not_started"].count() == 1
        assert window.status_lists["in_progress"].count() == 1
        assert window.status_lists["done"].count() == 1
        assert window.status_lists["in_review"].count() == 0

    def test_reload_populates_item_text_with_shot_name(self, qtbot: QtBot) -> None:
        fake = FakeApiClient(shots=_sample_shots())
        window = _make_window(qtbot, fake)

        window.reload_button.click()

        assert window.status_lists["not_started"].item(0).text() == "SHOT010"

    def test_reload_updates_status_label_with_total_count(self, qtbot: QtBot) -> None:
        fake = FakeApiClient(shots=_sample_shots())
        window = _make_window(qtbot, fake)

        window.reload_button.click()

        assert "3" in window.status_label.text()

    def test_reload_clears_previous_items_before_repopulating(self, qtbot: QtBot) -> None:
        fake = FakeApiClient(shots=_sample_shots())
        window = _make_window(qtbot, fake)
        window.reload_button.click()

        fake._shots = [{"id": 4, "name": "SHOT040", "status": "done"}]
        window.reload_button.click()

        assert window.status_lists["not_started"].count() == 0
        assert window.status_lists["done"].count() == 1

    def test_reload_shows_error_message_when_api_error_raised(self, qtbot: QtBot) -> None:
        fake = FakeApiClient(raise_on_list=ApiError(500, "Internal Server Error"))
        window = _make_window(qtbot, fake)

        window.reload_button.click()

        assert "Internal Server Error" in window.status_label.text()


class TestStatusChange:
    def test_selecting_shot_and_applying_status_calls_update_shot_status(
        self, qtbot: QtBot
    ) -> None:
        fake = FakeApiClient(shots=_sample_shots())
        window = _make_window(qtbot, fake)
        window.reload_button.click()

        list_widget = window.status_lists["not_started"]
        list_widget.setCurrentItem(list_widget.item(0))
        index = window.status_combo.findData("done")
        window.status_combo.setCurrentIndex(index)
        window.apply_status_button.click()

        assert fake.update_calls == [(1, "done")]

    def test_apply_status_reloads_shots_after_success(self, qtbot: QtBot) -> None:
        fake = FakeApiClient(shots=_sample_shots())
        window = _make_window(qtbot, fake)
        window.reload_button.click()

        list_widget = window.status_lists["not_started"]
        list_widget.setCurrentItem(list_widget.item(0))
        window.status_combo.setCurrentIndex(window.status_combo.findData("done"))
        window.apply_status_button.click()

        assert window.status_lists["not_started"].count() == 0
        assert window.status_lists["done"].count() == 2

    def test_apply_status_without_selection_shows_message_and_does_not_call_api(
        self, qtbot: QtBot
    ) -> None:
        fake = FakeApiClient(shots=_sample_shots())
        window = _make_window(qtbot, fake)
        window.reload_button.click()

        window.apply_status_button.click()

        assert fake.update_calls == []
        assert "選択" in window.status_label.text()

    def test_selecting_item_in_one_list_clears_selection_in_others(self, qtbot: QtBot) -> None:
        fake = FakeApiClient(shots=_sample_shots())
        window = _make_window(qtbot, fake)
        window.reload_button.click()

        not_started_list = window.status_lists["not_started"]
        in_progress_list = window.status_lists["in_progress"]
        not_started_list.setCurrentItem(not_started_list.item(0))
        in_progress_list.setCurrentItem(in_progress_list.item(0))

        assert not_started_list.selectedItems() == []
        assert len(in_progress_list.selectedItems()) == 1

    def test_apply_status_shows_error_message_when_api_error_raised(self, qtbot: QtBot) -> None:
        class FailingApiClient(FakeApiClient):
            def update_shot_status(self, shot_id: int, status: str) -> dict[str, Any]:
                raise ApiError(400, "Invalid status: bogus")

        fake = FailingApiClient(shots=_sample_shots())
        window = _make_window(qtbot, fake)
        window.reload_button.click()

        list_widget = window.status_lists["not_started"]
        list_widget.setCurrentItem(list_widget.item(0))
        window.apply_status_button.click()

        assert "Invalid status" in window.status_label.text()


class TestKeyboardAndAccessibility:
    def test_the_reload_and_apply_buttons_have_keyboard_shortcuts(self, qtbot: QtBot) -> None:
        window = _make_window(qtbot)

        assert window.reload_button.shortcut().toString() == "F5"
        assert window.apply_status_button.shortcut().toString() == "Ctrl+Return"

    def test_each_status_list_is_named_for_screen_readers(self, qtbot: QtBot) -> None:
        window = _make_window(qtbot)

        assert window.status_lists["in_progress"].accessibleName() == "作業中のショット一覧"
        assert window.status_lists["done"].accessibleName() == "完了のショット一覧"

    def test_the_status_combo_and_the_message_are_named(self, qtbot: QtBot) -> None:
        window = _make_window(qtbot)

        assert window.status_combo.accessibleName() == "変更後のステータス"
        assert window.status_label.accessibleName() == "状況メッセージ"

    def test_an_error_message_is_shown_in_the_error_color_and_cleared_on_success(
        self, qtbot: QtBot
    ) -> None:
        fake = FakeApiClient(shots=_sample_shots(), raise_on_list=ApiError(500, "Server error"))
        window = _make_window(qtbot, fake)

        window.reload_shots()

        assert "読み込みエラー" in window.status_label.text()
        assert "#b00020" in window.status_label.styleSheet()

        fake._raise_on_list = None
        window.reload_shots()

        assert window.status_label.styleSheet() == ""

    def test_the_apply_error_is_also_in_the_error_color(self, qtbot: QtBot) -> None:
        window = _make_window(qtbot, FakeApiClient(shots=_sample_shots()))
        window.reload_shots()

        window._on_apply_status_clicked()

        assert "ショットが選択されていません" in window.status_label.text()
        assert "#b00020" in window.status_label.styleSheet()
