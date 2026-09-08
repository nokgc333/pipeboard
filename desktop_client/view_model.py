"""APIレスポンス(dict)を表示用データへ変換する純粋関数群（DCC/PySide6非依存）。

`frontend/src/domain/status/status.ts`と表示順序・日本語ラベルを一致させる
（Webとデスクトップで同じドメインルールを共有する設計の一部）。
"""

from __future__ import annotations

from typing import Any

STATUS_ORDER: tuple[str, ...] = ("not_started", "in_progress", "in_review", "done")

STATUS_LABELS: dict[str, str] = {
    "not_started": "未着手",
    "in_progress": "作業中",
    "in_review": "レビュー",
    "done": "完了",
}


def is_valid_status(value: str) -> bool:
    """バックエンドのapp/domain/status_transition.pyのALLOWED_STATUSESと対になる検証関数。"""
    return value in STATUS_ORDER


def status_label(status: str) -> str:
    """ステータスの日本語表示ラベルを返す。未知の値はそのまま返す（表示が壊れないようにする）。"""
    return STATUS_LABELS.get(status, status)


def group_shots_by_status(shots: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """ショット一覧をステータスごとにグルーピングする。

    キーは常にSTATUS_ORDERの全ステータス（該当ショットが無くても空リストで存在する）。
    未知のstatus値を持つショットは、バックエンドのバリデーションを通っていない不整合データ
    とみなし、いずれの列にも表示しない（防御的に除外する。呼び出し元はUI上でエラーとして
    扱わず単に非表示になる想定）。
    """
    grouped: dict[str, list[dict[str, Any]]] = {status: [] for status in STATUS_ORDER}
    for shot in shots:
        status = shot.get("status")
        if status in grouped:
            grouped[status].append(shot)
    return grouped
