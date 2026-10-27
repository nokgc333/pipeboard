"""OpenAPI 定義を JSON で書き出す。フロントエンドの型・クライアントの生成元になる。"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from app.main import app


def openapi_text() -> str:
    return json.dumps(app.openapi(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: python -m app.export_openapi <output.json>", file=sys.stderr)
        return 2
    Path(argv[1]).write_text(openapi_text(), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
