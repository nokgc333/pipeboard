# ADR-0006: マイグレーションと PostgreSQL 対応、SQLite は WAL

## Status
Accepted (2026-10-27). [ADR-0003](0003-sqlite.md) を補う(SQLite は既定のまま残す)。

## Context
テーブルを起動時に `create_all` で作る方式では、列の追加(階層・監査ログ・検査結果)を、既存のデータを持つデータベースへ安全に反映できない。
また、複数人で使う運用では、SQLite の書き込みロックと、1 台に閉じた構成が限界になる。

## Decision
- スキーマは Alembic のマイグレーションで管理する(`backend/app/migrations/`、パッケージ内に置くので、Docker イメージにも入る)。起動時・seed・テストは `python -m app.migrate` と同じ経路で最新にする。
- モデルとマイグレーションが食い違うと、テストが落ちる(`compare_metadata`)。空の DB から最新までの再現、前の版からデータを保ったままの更新、`downgrade` も試す。
- マイグレーション導入前に作られた DB は、`python -m app.migrate stamp 0001` で「適用済み」にしてから使う(運用手順書)。
- 既定は SQLite のまま。ファイルの SQLite は WAL・`synchronous=NORMAL`・`busy_timeout=5000` にし、読み取りが書き込みを待たないようにする。外部キーも有効にする。
- `PIPEBOARD_DATABASE_URL` で PostgreSQL(`postgresql+psycopg://...`)に切り替えられる。ドライバは `requirements-postgres.txt`(任意)。CI は PostgreSQL のサービスコンテナで、マイグレーションと API の主要な操作を実行する。

## Consequences
良い: スキーマ変更を、履歴とテストつきで配れる。小さく始め(SQLite)、必要なときに PostgreSQL へ移れる。
悪い: SQLite の `ALTER` の制限のため、マイグレーションは `batch` モードで書く。外部キー制約に名前が要る。
      SQLite から PostgreSQL へのデータ移行の道具は、用意していない(利用者が `pg_dump` 相当で行う)。
