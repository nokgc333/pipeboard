"""公開ゲートの判定(純粋関数)。レビュー・完了へ進むには、必須の検査すべての最新結果が合格であること。"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

GATED_STATUSES = frozenset({"in_review", "done"})


@dataclass(frozen=True)
class CheckSummary:
    tool: str
    passed: bool


@dataclass(frozen=True)
class GateDecision:
    allowed: bool
    reason: str | None = None


def evaluate_gate(
    target_status: str,
    required_tools: tuple[str, ...],
    latest_checks: Mapping[str, CheckSummary],
) -> GateDecision:
    if target_status not in GATED_STATUSES or not required_tools:
        return GateDecision(allowed=True)

    failed = [t for t in required_tools if t in latest_checks and not latest_checks[t].passed]
    missing = [t for t in required_tools if t not in latest_checks]
    if not failed and not missing:
        return GateDecision(allowed=True)

    parts: list[str] = []
    if failed:
        parts.append(f"Failed checks: {', '.join(failed)}")
    if missing:
        parts.append(f"Missing checks: {', '.join(missing)}")
    return GateDecision(allowed=False, reason="; ".join(parts))
