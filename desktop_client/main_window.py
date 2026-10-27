"""PipeBoard mini のPySide6デスクトップクライアント メインウィンドウ。

`api_client: ShotsApi`を注入されるだけで動作する疎結合設計にすることで、
`QT_QPA_PLATFORM=offscreen`のヘッドレスQApplication上で本物のPySide6ウィジェットとして
テストできる（scene_doctor/ui/panel.py, tests/test_panel.pyと同じ手法）。requestsは
直接呼ばず、必ずapi_client経由でバックエンドと通信する。
"""

from __future__ import annotations

from typing import Any, Protocol

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from desktop_client.api_client import ApiError
from desktop_client.view_model import STATUS_LABELS, STATUS_ORDER, group_shots_by_status

# QListWidgetItemにショットIDを紐付けるためのカスタムデータロール
SHOT_ID_ROLE = int(Qt.ItemDataRole.UserRole)
ERROR_COLOR = "#b00020"


class ShotsApi(Protocol):
    def list_shots(self) -> list[dict[str, Any]]: ...

    def update_shot_status(self, shot_id: int, status: str) -> dict[str, Any]: ...


class PipeBoardMainWindow(QMainWindow):
    """ステータスごとの列（QListWidget）でショット一覧を表示するカンバン風メインウィンドウ。

    Args:
        api_client: バックエンドと通信するShotsApi(PipeBoardApiClientが満たす)（テストではfakeを注入する）。
    """

    def __init__(self, api_client: ShotsApi, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("PipeBoard mini")

        self._api_client = api_client
        self._shots: list[dict[str, Any]] = []
        self.status_lists: dict[str, QListWidget] = {}

        self._build_ui()
        self._connect_signals()

    def _build_ui(self) -> None:
        central = QWidget(self)
        layout = QVBoxLayout(central)

        toolbar = QHBoxLayout()
        self.reload_button = QPushButton("更新", central)
        self.reload_button.setShortcut("F5")
        self.reload_button.setToolTip("一覧を再取得する (F5)")
        toolbar.addWidget(self.reload_button)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        columns_layout = QHBoxLayout()
        for status in STATUS_ORDER:
            group = QGroupBox(STATUS_LABELS[status], central)
            group_layout = QVBoxLayout(group)
            list_widget = QListWidget(group)
            list_widget.setAccessibleName(f"{STATUS_LABELS[status]}のショット一覧")
            group_layout.addWidget(list_widget)
            columns_layout.addWidget(group)
            self.status_lists[status] = list_widget
        layout.addLayout(columns_layout)

        status_change_bar = QHBoxLayout()
        status_change_bar.addWidget(QLabel("選択中ショットのステータス変更:", central))
        self.status_combo = QComboBox(central)
        for status in STATUS_ORDER:
            self.status_combo.addItem(STATUS_LABELS[status], status)
        self.status_combo.setAccessibleName("変更後のステータス")
        self.apply_status_button = QPushButton("適用", central)
        self.apply_status_button.setShortcut("Ctrl+Return")
        self.apply_status_button.setToolTip("選択中のショットに適用する (Ctrl+Enter)")
        status_change_bar.addWidget(self.status_combo)
        status_change_bar.addWidget(self.apply_status_button)
        layout.addLayout(status_change_bar)

        self.status_label = QLabel("0 shot(s)", central)
        self.status_label.setAccessibleName("状況メッセージ")
        layout.addWidget(self.status_label)

        central.setLayout(layout)
        self.setCentralWidget(central)

    def _connect_signals(self) -> None:
        self.reload_button.clicked.connect(self.reload_shots)
        self.apply_status_button.clicked.connect(self._on_apply_status_clicked)
        for list_widget in self.status_lists.values():
            list_widget.itemSelectionChanged.connect(self._on_item_selection_changed)

    def reload_shots(self) -> None:
        """一覧をバックエンドから再取得し、ステータス列を再描画する。"""
        try:
            self._shots = self._api_client.list_shots()
        except ApiError as exc:
            self._show_error(f"読み込みエラー: {exc.title}")
            return
        self._rebuild_lists()

    def _show_error(self, message: str) -> None:
        self.status_label.setStyleSheet(f"color: {ERROR_COLOR};")
        self.status_label.setText(message)

    def _rebuild_lists(self) -> None:
        grouped = group_shots_by_status(self._shots)
        for status, list_widget in self.status_lists.items():
            list_widget.clear()
            for shot in grouped[status]:
                item = QListWidgetItem(shot["name"])
                item.setData(SHOT_ID_ROLE, shot["id"])
                list_widget.addItem(item)
        self.status_label.setStyleSheet("")
        self.status_label.setText(f"{len(self._shots)} shot(s)")

    def _selected_shot_id(self) -> int | None:
        for list_widget in self.status_lists.values():
            selected = list_widget.selectedItems()
            if selected:
                return int(selected[0].data(SHOT_ID_ROLE))
        return None

    def _on_item_selection_changed(self) -> None:
        """複数列にまたがる選択を防ぎ、常に単一のショットだけが選択された状態を保つ。"""
        sender = self.sender()
        for list_widget in self.status_lists.values():
            if list_widget is not sender and list_widget.selectedItems():
                list_widget.blockSignals(True)
                list_widget.clearSelection()
                list_widget.blockSignals(False)

    def _on_apply_status_clicked(self) -> None:
        shot_id = self._selected_shot_id()
        if shot_id is None:
            self._show_error("ショットが選択されていません")
            return

        new_status = self.status_combo.currentData()
        try:
            self._api_client.update_shot_status(shot_id, new_status)
        except ApiError as exc:
            self._show_error(f"更新エラー: {exc.title}")
            return
        self.reload_shots()
