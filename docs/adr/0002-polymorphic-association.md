# ADR-0002: VERSION/COMMENTのポリモーフィック関連採用

## Status
Accepted (2026-09-07)

## Context
バージョン画像・コメントは、ショットにもアセットにも同じ形で紐づく。それぞれに専用テーブル
（shot_versions, asset_versions等）を作ると、ロジックの重複とテーブル数の増加を招く。

## Decision
`versions`・`comments`テーブルに`item_type`（'shot'|'asset'）+ `item_id`のポリモーフィック関連を
採用する。SQLiteのFOREIGN KEY制約は単一テーブルにしか張れないため、DBレベルのFK制約は設定せず、
アプリ層（`domain/items.py`の`_get_or_404`、Pydanticバリデーション）で参照整合性を保証する。
検索性能のため`(item_type, item_id)`の複合インデックスを両テーブルに付与する。

## Consequences
良い: テーブル数を4つに抑えられ、shots/assets双方で同じversions/commentsロジックを再利用できる
悪い: DBレベルの参照整合性保証がないため、アプリ層のバグがあれば孤立レコードが発生しうる
     （v1では削除時のカスケード処理をアプリ層のテストでカバーすることで許容範囲と判断）

## Alternatives Considered
- shot_versions / asset_versions の別テーブル化: テーブル数が倍増し、ロジックの重複が生じるため却下
