"""PipeBoard mini デスクトップクライアントのエントリポイント。

`PIPEBOARD_API_BASE_URL`環境変数でバックエンドのURLを指定できる（未指定時はローカル既定値）。
"""

from __future__ import annotations

import os
import sys

from PySide6.QtWidgets import QApplication

from desktop_client.api_client import PipeBoardApiClient
from desktop_client.main_window import PipeBoardMainWindow

DEFAULT_BASE_URL = "http://localhost:8000"


def main() -> int:
    base_url = os.environ.get("PIPEBOARD_API_BASE_URL", DEFAULT_BASE_URL)
    app = QApplication(sys.argv)

    api_client = PipeBoardApiClient(base_url)
    window = PipeBoardMainWindow(api_client)
    window.reload_shots()
    window.resize(900, 600)
    window.show()

    return app.exec()


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
