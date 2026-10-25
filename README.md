# PipeBoard mini

ショット/アセットの進捗をカンバン形式で管理し、Houdiniから直接ステータスを更新できるミニ・プロダクショントラッカー（ShotGrid/Kitsuの縮小版）。

## 目的・背景

ショット・アセットの進捗がExcelや口頭連携で属人化するのは、中小規模スタジオで頻発する課題です。PipeBoard miniはこれをWebダッシュボードとして自作し、さらにHoudiniから直接ステータス更新できる導線（`scripts/houdini_status_update.py`）を用意することで、「DCCとWebをまたぐ横断ツール」を実際に動くコードで証明します。

Houdiniで作業を終えるたびに、ブラウザに切り替えて対象ショットを探し、ステータスをドロップダウンで変更する——という往復作業は1回あたり数十秒でも、1日に何十ショットも触るアーティストにとっては地味に積み重なる手戻りです。`houdini_status_update.py`はHoudini（Python Shell）から離れずにこの更新を1行の関数呼び出しで完結させます。hou非依存の設計のため、実機検証では実際に稼働中のバックエンドに対してこの関数を直接呼び出し、変更がブラウザのカンバンボードへ即座に反映されることを確認済みです（Houdini本体からの呼び出しではなく、同じ関数を単体で実行しての確認）。

さらに`desktop_client/`では、同じFastAPI REST APIを叩くだけのPySide6デスクトップクライアントを追加しています。バックエンドは無改修のまま、Web（Next.js）とデスクトップ（PySide6）という2つの異なる入り口から同一のビジネスロジックを使い回せることを、実際に動くコードで証明するのが狙いです。プロダクションスタジオでは「ブラウザは開きたくないがDCC/ローカルアプリからは触りたい」というアーティストの運用も現実的にあり得るため、バックエンドを共有したまま入り口だけを増やせる設計であることの実証を兼ねています。

詳細な要件定義・設計判断は [docs/要件定義書.md](docs/要件定義書.md) / [docs/仕様書.md](docs/仕様書.md) を参照してください。

## 構成

```
pipeboard/
├── frontend/       Next.js 15 + TypeScript（カンバンボード・詳細画面）
├── backend/        FastAPI + SQLAlchemy + SQLite（REST API）
├── desktop_client/ PySide6デスクトップクライアント（同一REST APIを叩く別フロントエンド）
├── scripts/        houdini_status_update.py（Houdini Python ShellからのFR-007連携）
└── docs/           要件定義書・仕様書・ADR
```

## 技術スタック

- **frontend**: Next.js 15.5 / React 19 / TypeScript / Tailwind CSS v4 / Vitest + Testing Library / Playwright
- **backend**: FastAPI / SQLAlchemy 2.0 / Pydantic v2 / pytest / mypy(strict)
- **desktop_client**: PySide6 / requests / pytest + pytest-qt / mypy(strict)
- **scripts**: requests のみ（hou非依存、どのPython環境からでも実行可能）

## インストール・起動（ローカル）

```bash
# バックエンド
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m app.seed          # デモデータ投入
uvicorn app.main:app --reload --port 8000

# フロントエンド（別ターミナル）
cd frontend
npm install
npm run dev
```

`http://localhost:3000` でカンバンボードが表示されます。

### Docker Composeで起動する場合

```bash
docker compose up --build
```

### Houdiniからステータスを更新する

Houdiniの Python Shell で:

```python
import sys
sys.path.append("/path/to/pipeboard/scripts")
from houdini_status_update import send_status_update
send_status_update("http://localhost:8000", "shot", 1, "in_review")
```

### PySide6デスクトップクライアントを起動する

バックエンドを起動した状態で、別ターミナルから:

```bash
cd desktop_client
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cd ..                                 # リポジトリルートに戻る（desktop_clientをパッケージとしてimportするため必須）
python -m desktop_client.app          # PIPEBOARD_API_BASE_URLで接続先を変更可能（既定 http://localhost:8000）
```

> `desktop_client`ディレクトリの中にいたままだと`python -m desktop_client.app`は
> `ModuleNotFoundError: No module named 'desktop_client'`で失敗する（`desktop_client`自身が
> パッケージ名のため、その親ディレクトリがカレントディレクトリである必要がある）。
> venvの有効化は`desktop_client/`内で行って構わないが、起動コマンドは必ずリポジトリルートで実行すること。

ステータスごとの列（未着手/作業中/レビュー/完了）でショット一覧が表示され、ショットを選択してコンボボックスから新しいステータスを選んで「適用」を押すと、Webのカンバンボードと同じバックエンドAPI（`PATCH /shots/{id}/status`）経由でDBが更新されます。「更新」ボタンで一覧を再取得できます。

## テスト

```bash
# バックエンド（80テスト、カバレッジ95%）
cd backend && pytest --cov=app --cov-report=term-missing

# フロントエンド（42テスト、domain/lib層カバレッジ80%以上）
cd frontend && npm run test -- --coverage
npm run type-check

# Houdini連携スクリプト（7テスト、hou非依存）
cd scripts && pytest tests/ -v

# デスクトップクライアント（46テスト、カバレッジ99%、本物のPySide6ウィジェットをheadlessで検証）
cd desktop_client && QT_QPA_PLATFORM=offscreen pytest --cov=. --cov-report=term-missing
```

実際にバックエンド+フロントエンドを起動し、ブラウザ上でカンバン表示・ステータス変更（楽観的更新→API反映）・コメント投稿がDBまで正しく反映されることをE2Eで確認済みです。デスクトップクライアントについても、実際に稼働中のバックエンド（シード済みデータ）に対して`QT_QPA_PLATFORM=offscreen`下でメインウィンドウを起動し、実データの一覧取得・カンバン列への表示・ステータス変更操作がバックエンドDBまで正しく反映されることを確認済みです（ウィジェットの内部状態をコードで検証、目視確認は行っていません）。

## 認証・セキュリティ設定

| 環境変数 | 既定値 | 意味 |
| --- | --- | --- |
| `PIPEBOARD_AUTH_MODE` | `local` | `local`=認証なし（自分のマシン専用） / `token`=Bearerトークン必須 |
| `PIPEBOARD_API_TOKENS` | なし | `token` モードで必須。`viewer=...,editor=...,admin=...`（各12文字以上） |
| `PIPEBOARD_CORS_ORIGINS` | `http://localhost:3000` | 許可するOrigin（カンマ区切り）。`*` は明示した場合のみ |
| `PIPEBOARD_RATE_LIMIT_READ_PER_MINUTE` | `300` | 読み取りの上限（IPごと、1分あたり） |
| `PIPEBOARD_RATE_LIMIT_WRITE_PER_MINUTE` | `60` | 書き込みの上限（同上） |
| `PIPEBOARD_API_TOKEN` | なし | デスクトップクライアント・Houdiniスクリプトが送るトークン |
| `NEXT_PUBLIC_API_TOKEN` | なし | Webフロントが送るトークン（配信されるJSに含まれるため、閲覧専用トークンか信頼できるネットワークに限る） |

```bash
export PIPEBOARD_AUTH_MODE=token
export PIPEBOARD_API_TOKENS="viewer=$(openssl rand -hex 16),editor=$(openssl rand -hex 16),admin=$(openssl rand -hex 16)"
```

- ロール: `viewer`=閲覧 / `editor`=作成・更新・ステータス変更・コメント・アップロード / `admin`=削除を含む全操作。未認証は401、権限不足は403。
- Docker Compose はポートを `127.0.0.1` にだけ公開している。外部に出す場合は、`token` モードとTLS（リバースプロキシ）を併用すること。
- アップロードは、拡張子・Content-Type・先頭バイト（PNG/JPEG/WebP）を検証し、10MBを超えると途中で打ち切る。
- フロントエンドは、CSP・HSTS・`X-Content-Type-Options`・`X-Frame-Options` などのヘッダを付ける（`frontend/src/lib/security-headers.mjs`）。

## 既知の制限事項（Not in scope, v1）

- **認証・権限管理**: 既定の `local` モードは認証なし。外部に公開する場合は `token` モードにする（[ADR-0005](docs/adr/0005-token-authentication.md)）。個人ごとのログイン・監査ログは未実装
- **同時編集の競合制御**: バージョン採番・ステータス更新ともに楽観ロックを実装していない（要件定義書§16.6参照）
- **ドラッグ&ドロップ**: カンバンのステータス変更はセレクトボックスのみ対応。HTML5 Drag and Drop APIによる列間ドラッグは未実装（キーボード操作でも完結できることをアクセシビリティ上優先し、v1のスコープからは意図的に外した）
- **E2Eテストの自動実行範囲**: `frontend/e2e/kanban.spec.ts`はCI（`ci-frontend.yml`のe2e-testジョブ）で自動実行されるが、Docker Compose経由の統合起動そのものはCI化していない
- **desktop_clientのスコープ**: ショットのステータス閲覧・変更のみを実装し、アセット一覧・バージョンアップロード・コメント機能はUIとしては未実装（`api_client.py`にはメソッドを用意済みだが`main_window.py`からは未使用）。Web版で完結している機能をデスクトップでも全て再実装するのではなく、「同一バックエンドを複数フロントエンドから使い回せる」ことの実証に必要な範囲に絞った

## Design Decisions

- **DRYなCRUDファクトリ**: shots/assetsは同一スキーマのため、`backend/app/domain/items.py`の`create_item_router()`で共通化し、ルータファイル自体は1行で済ませている
- **VERSION/COMMENTのポリモーフィック関連**: DBレベルのFK制約を持たず、アプリ層で参照整合性を保証（[ADR-0002](docs/adr/0002-polymorphic-association.md)）
- **SQLiteを正本DBとして採用**: デモ規模のデータ量に対しPostgreSQL導入は過剰と判断（[ADR-0003](docs/adr/0003-sqlite.md)）
- **アップロードファイル名はUUID生成**: 元ファイル名をそのまま使わずパストラバーサル・衝突を防止（SEC-002）
- **拡張子とMIME typeの両方を検証**: なりすまし拡張子によるアップロード攻撃を防止（SEC-001）
- **desktop_clientのview_model/ウィジェット層分離**: `desktop_client/view_model.py`（DCC/PySide6非依存の純粋関数）と`desktop_client/main_window.py`（PySide6ウィジェット、`api_client`を注入されるだけの疎結合設計）を分離することで、`QT_QPA_PLATFORM=offscreen` + `pytest-qt`のheadless環境で本物のPySide6ウィジェットをTDDできるようにした。これは別プロジェクト（scene_doctor）のHoudini向けPySide6パネルで採用したports-and-adapters的設計（scene_doctorのADR-0007相当）と同じ思想を踏襲している
- **api_clientは`requests`のみに依存**: `scripts/houdini_status_update.py`と同様、注入可能な`session`でモックしテストできる設計とし、PySide6は`api_client.py`から一切importしない（バックエンド通信ロジックとGUIロジックの責務分離）

## ライセンス

MIT License（[LICENSE](LICENSE)参照）
