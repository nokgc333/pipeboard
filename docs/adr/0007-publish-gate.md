# ADR-0007: 公開ゲート(検査に通らないものは、レビュー・完了に進めない)

## Status
Accepted (2026-10-27)

## Context
scene-doctor(Houdini のシーン検査)や unibridge(USD の整合検査)は、問題を見つけても、進捗管理の側が無視すれば意味がない。
検査の結果を進捗の遷移に結び付け、問題のあるものが「完了」にならないようにしたい。

## Decision
- 検査結果は、ツール間で共通のレポート形式(`schema_version: "1"`、`tool`、`has_errors`、`findings[]`)で、`POST /shots|assets/{id}/checks` に提出する。形式が違えば 422。`has_errors` が真なら不合格。
- `PIPEBOARD_REQUIRED_CHECKS=scene-doctor,unibridge` で、必須の検査を指定する。未設定ならゲートは無効(既存の運用を変えない)。
- 判定は純粋関数 `evaluate_gate`(`app/domain/publish_gate.py`)。`in_review` と `done` への遷移だけを対象にし、必須の検査それぞれの最新の結果がすべて合格のときだけ通す。足りなければ 409 と、`Failed checks: ...; Missing checks: ...` の理由を返す。
- 判定の純粋関数は、ミューテーションテストで 31 件中 31 件を検出する(CI で週 1 回)。

## Consequences
良い: Houdini から、サムネイル・検査結果・ステータス変更を 1 回で出せ、止まった理由がその場で分かる(実機で確認済み、`docs/verification/`)。
悪い: 検査結果は、提出された内容を信じる(ツールが本当に走ったかは、署名などでは確かめない)。
      シーンが変わったあとの古い合格が残る。結果を「いつの版に対するものか」と結び付けるのは、今後の課題。
