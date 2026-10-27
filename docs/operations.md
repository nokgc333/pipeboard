# 運用手順書

## 起動

### Docker Compose(推奨)

```bash
cp .env.example .env      # 必要なら編集する
docker compose up --build
```

- バックエンドが `/health` で正常と答えてから、フロントエンドが起動する
- 起動のたびに、マイグレーションを最新まで適用し、デモデータを(空のときだけ)入れる
- ポートは `127.0.0.1` にだけ公開している。外に出すときは、`PIPEBOARD_AUTH_MODE=token` と TLS(リバースプロキシ)を併用する

### 公開済みのイメージ

タグ(`v0.2.0` など)を push すると、`ghcr.io/nokgc333/pipeboard-backend` と `pipeboard-frontend` に、版と `latest` で公開される。

## 状態の確認

| 確認 | コマンド | 正常 |
| --- | --- | --- |
| 生存 | `curl localhost:8000/healthz` | `{"status":"ok"}` |
| 準備完了(DB まで) | `curl localhost:8000/health` | `{"status":"ok","database":"ok","version":"..."}`。DB に繋がらないと 503 |
| 変更の履歴 | `GET /audit-log`(admin) | 誰が・いつ・何を |

## データの場所

| 内容 | Docker | 設定 |
| --- | --- | --- |
| データベース | ボリューム `pipeboard_db`(`/app/data/pipeboard.db`) | `PIPEBOARD_DATABASE_URL` |
| アップロード画像 | ボリューム `uploads`(`/app/uploads`) | `PIPEBOARD_UPLOAD_DIR` |

## バックアップ

データベースと画像の両方を、同じ時点で取る(画像だけ・DB だけを戻すと、参照が食い違う)。

### SQLite(既定)

```bash
# 動かしたまま、整合した複製を作る(WAL でも安全)
docker compose exec backend python -c "import sqlite3; s=sqlite3.connect('/app/data/pipeboard.db'); d=sqlite3.connect('/app/data/backup.db'); s.backup(d)"
docker compose cp backend:/app/data/backup.db ./backup-$(date +%F).db
docker compose cp backend:/app/uploads ./uploads-$(date +%F)
```

`cp` でファイルを直接コピーしない(WAL の書き込み途中の内容が混ざる)。

### PostgreSQL

```bash
pg_dump --format=custom --file=pipeboard-$(date +%F).dump "$DATABASE_URL"
```

## 復旧

1. サービスを止める: `docker compose down`
2. データベースを戻す
   - SQLite: バックアップのファイルを、ボリュームの `pipeboard.db` に置き換える
   - PostgreSQL: `pg_restore --clean --dbname "$DATABASE_URL" pipeboard-YYYY-MM-DD.dump`
3. 画像を戻す: バックアップの `uploads` を、ボリュームに置き換える
4. 起動する: `docker compose up`(起動時にマイグレーションが走り、古いバックアップでも最新の形になる)
5. `/health` が `ok` で、ボードにショットが出ることを確かめる

## 更新(アップグレード)

1. バックアップを取る
2. 新しい版のイメージを取得して起動する(マイグレーションは自動)
3. 戻したいときは、イメージを前の版に戻し、バックアップからデータベースを復元する(マイグレーションの `downgrade` は、データを持つ本番では使わない)

### マイグレーション導入前のデータベース(0.1.0 以前)を使い続けるとき

テーブルがすでにあるため、最初のマイグレーションは、作らず「適用済み」にする。

```bash
docker compose run --rm backend python -m app.migrate stamp 0001
docker compose up
```

(以降のマイグレーションは、起動時に自動で適用される。)

## 設定

すべての環境変数は [`.env.example`](../.env.example) にある。

| 目的 | 変数 |
| --- | --- |
| 認証 | `PIPEBOARD_AUTH_MODE`、`PIPEBOARD_API_TOKENS` |
| 公開ゲート | `PIPEBOARD_REQUIRED_CHECKS=scene-doctor,unibridge` |
| Webhook | `PIPEBOARD_WEBHOOK_URL`、`PIPEBOARD_WEBHOOK_SECRET` |
| 負荷の制限 | `PIPEBOARD_RATE_LIMIT_READ_PER_MINUTE`、`PIPEBOARD_RATE_LIMIT_WRITE_PER_MINUTE` |

不正な設定は、起動時に例外で止まる(動いてから気づかないため)。

## Webhook の受け取り

本文は JSON(`action`、`actor`、`item_type`、`item_id`、`detail`、`at`)。ヘッダ `X-PipeBoard-Signature: sha256=<HMAC-SHA256(本文, 秘密鍵)>` を、受け取り側で検証する。送信は、変更のコミット後に 1 回だけで、失敗しても再送しない(失敗はログに `webhook delivery failed` と出る)。

## 困ったとき

| 症状 | 原因と対処 |
| --- | --- |
| `/health` が 503 | データベースに繋がらない。`PIPEBOARD_DATABASE_URL`、ボリューム、PostgreSQL の起動を確認する |
| 起動時に `PIPEBOARD_... must ...` で止まる | 設定の誤り。メッセージの指す変数を直す |
| 完了に進めない(409 `Missing checks: ...`) | 公開ゲートが有効。必須の検査の結果を `POST /shots/{id}/checks` で提出する |
| 429 | レート制限。`Retry-After` の秒数だけ待つか、上限を上げる |
| 画像が表示されない | `PIPEBOARD_UPLOAD_DIR` のボリュームが、バックアップから戻されていない |
