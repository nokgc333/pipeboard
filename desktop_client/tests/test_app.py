"""app.py エントリポイントのwiring検証。

実イベントループ（QApplication.exec）は起動せず、QApplication/APIクライアント/
メインウィンドウの生成呼び出しをモックして「何をどう組み立てるか」だけを検証する。
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from desktop_client import app as app_module


def test_main_uses_default_base_url_when_env_not_set(monkeypatch) -> None:
    monkeypatch.delenv("PIPEBOARD_API_BASE_URL", raising=False)
    fake_qapp = MagicMock()
    fake_qapp.exec.return_value = 0
    fake_window = MagicMock()

    with (
        patch.object(app_module, "QApplication", return_value=fake_qapp),
        patch.object(app_module, "PipeBoardApiClient") as api_cls,
        patch.object(app_module, "PipeBoardMainWindow", return_value=fake_window),
    ):
        exit_code = app_module.main()

    api_cls.assert_called_once_with(app_module.DEFAULT_BASE_URL)
    fake_window.reload_shots.assert_called_once()
    fake_window.show.assert_called_once()
    assert exit_code == 0


def test_main_uses_env_base_url_when_set(monkeypatch) -> None:
    monkeypatch.setenv("PIPEBOARD_API_BASE_URL", "http://example.com:9000")
    fake_qapp = MagicMock()
    fake_qapp.exec.return_value = 0

    with (
        patch.object(app_module, "QApplication", return_value=fake_qapp),
        patch.object(app_module, "PipeBoardApiClient") as api_cls,
        patch.object(app_module, "PipeBoardMainWindow", return_value=MagicMock()),
    ):
        app_module.main()

    api_cls.assert_called_once_with("http://example.com:9000")


def test_main_returns_qapplication_exec_code(monkeypatch) -> None:
    monkeypatch.delenv("PIPEBOARD_API_BASE_URL", raising=False)
    fake_qapp = MagicMock()
    fake_qapp.exec.return_value = 1

    with (
        patch.object(app_module, "QApplication", return_value=fake_qapp),
        patch.object(app_module, "PipeBoardApiClient"),
        patch.object(app_module, "PipeBoardMainWindow", return_value=MagicMock()),
    ):
        exit_code = app_module.main()

    assert exit_code == 1
