"""Houdini 実機のパブリッシュ検証。`hython scripts/verify_houdini_publish.py` で実行する。

必要な環境変数: PIPEBOARD_URL(既定 http://localhost:8000)、PIPEBOARD_API_TOKEN、
PIPEBOARD_ITEM_ID(対象のショット)、PIPEBOARD_PASS_REPORT / PIPEBOARD_FAIL_REPORT(検査レポートのパス)。
バックエンドは PIPEBOARD_REQUIRED_CHECKS=unibridge で起動しておく(公開ゲートを確かめるため)。
結果は 1 行 1 項目の `CHECK <名前> <PASS|FAIL> <詳細>` で出力する。
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import hou

sys.path.insert(0, str(Path(__file__).resolve().parent))

from houdini_publish import PublishBlocked, publish, write_cop_thumbnail  # noqa: E402

BASE = os.environ.get("PIPEBOARD_URL", "http://localhost:8000")
ITEM_ID = int(os.environ["PIPEBOARD_ITEM_ID"])


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"CHECK {name} {'PASS' if ok else 'FAIL'} {detail}")


def main() -> None:
    print(f"HOUDINI_VERSION {hou.applicationVersionString()}")
    with tempfile.TemporaryDirectory() as tmp:
        thumb = write_cop_thumbnail(hou, Path(tmp) / "thumb.png", 320, 180)
        size = thumb.stat().st_size if thumb.exists() else 0
        check(
            "thumbnail_is_written_as_png",
            size > 0 and thumb.read_bytes()[:4] == b"\x89PNG",
            f"{size} bytes",
        )

        try:
            publish(
                BASE,
                "shot",
                ITEM_ID,
                thumb,
                report_path=os.environ["PIPEBOARD_FAIL_REPORT"],
                status="in_review",
            )
            check("gate_blocks_a_failed_check", False, "was not blocked")
        except PublishBlocked as exc:
            check("gate_blocks_a_failed_check", "Failed checks: unibridge" in str(exc), str(exc))

        result = publish(
            BASE,
            "shot",
            ITEM_ID,
            thumb,
            report_path=os.environ["PIPEBOARD_PASS_REPORT"],
            status="in_review",
        )
        check(
            "version_is_uploaded",
            result["version"]["version_number"] >= 2,
            str(result["version"]["version_number"]),
        )
        check("passing_check_is_accepted", result["check"]["passed"] is True, "")
        check("status_moves_to_review_after_the_gate_passes", result["status"] == "in_review", "")


main()
