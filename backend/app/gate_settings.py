"""公開ゲートで必須にする検査の設定(PIPEBOARD_REQUIRED_CHECKS=scene-doctor,unibridge)。未設定ならゲートは無効。"""

from __future__ import annotations

import os
import re

from app.schemas.checks import TOOL_PATTERN

_TOOL = re.compile(TOOL_PATTERN)


def load_required_checks() -> tuple[str, ...]:
    raw = os.environ.get("PIPEBOARD_REQUIRED_CHECKS", "")
    tools: list[str] = []
    for part in filter(None, (p.strip() for p in raw.split(","))):
        if not _TOOL.match(part):
            raise ValueError(
                f"PIPEBOARD_REQUIRED_CHECKS has an invalid tool name '{part}' "
                "(lowercase letters, digits, '-' and '_', up to 30 characters)"
            )
        if part not in tools:
            tools.append(part)
    return tuple(tools)
