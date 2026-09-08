"""pytest共通設定。

`main_window.py`は本物のPySide6ウィジェットをヘッドレスで動かしてテストする
（`QT_QPA_PLATFORM=offscreen`）。ディスプレイのないCI環境でもQApplicationを生成できるように、
他のテストモジュールがPySide6をimportする前（collection開始時点）に環境変数を設定する
（scene_doctor/tests/conftest.pyと同じパターン）。
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
