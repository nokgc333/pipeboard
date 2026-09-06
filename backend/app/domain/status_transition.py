"""ステータス遷移ルールを純粋関数として切り出す（tonihaya-calendarのdomain分離パターンを踏襲）。

v1では全遷移を許可する設計判断とした（要件定義書FR-001）。
理由: 承認フローや権限ロールを持たない個人開発ツールにおいて、遷移制限を厳格化しても
UXの改善に寄与せず、実装・テストのコストが増えるだけと判断したため。
本関数はバリデーション（未定義のstatus値の拒否）のみを担う。
"""

from __future__ import annotations

ALLOWED_STATUSES = frozenset({"not_started", "in_progress", "in_review", "done"})


def is_valid_status(status: str) -> bool:
    """指定されたstatus文字列がALLOWED_STATUSESに含まれるかを検証する。"""
    return status in ALLOWED_STATUSES
