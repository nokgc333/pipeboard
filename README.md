# PipeBoard mini

ショット/アセットの進捗をカンバン形式で管理し、Houdiniから直接ステータスを更新できるミニ・プロダクショントラッカー（ShotGrid/Kitsuの縮小版）。

## 目的・背景

ショット・アセットの進捗がExcelや口頭連携で属人化するのは、中小規模スタジオで頻発する課題です。PipeBoard miniはこれをWebダッシュボードとして自作し、さらにHoudiniから直接ステータス更新できる導線（`scripts/houdini_status_update.py`）を用意することで、「DCCとWebをまたぐ横断ツール」を実際に動くコードで証明します。

詳細な要件定義・設計判断は [docs/要件定義書.md](docs/要件定義書.md) / [docs/仕様書.md](docs/仕様書.md) を参照してください。

## 構成

```
pipeboard/
├── frontend/   Next.js 15 + TypeScript（カンバンボード・詳細画面）
├── backend/    FastAPI + SQLAlchemy + SQLite（REST API）
├── scripts/    houdini_status_update.py（Houdini Python ShellからのFR-007連携）
└── docs/       要件定義書・仕様書・ADR
```

## 技術スタック

- **frontend**: Next.js 15.5 / React 19 / TypeScript / Tailwind CSS v4 / Vitest + Testing Library / Playwright
- **backend**: FastAPI / SQLAlchemy 2.0 / Pydantic v2 / pytest / mypy(strict)
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

## テスト

```bash
# バックエンド（30テスト、カバレッジ98%）
cd backend && pytest --cov=app --cov-report=term-missing

# フロントエンド（32テスト、domain/lib層カバレッジ100%）
cd frontend && npm run test -- --coverage
npm run type-check

# Houdini連携スクリプト（5テスト、hou非依存）
cd scripts && pytest tests/ -v
```

実際にバックエンド+フロントエンドを起動し、ブラウザ上でカンバン表示・ステータス変更（楽観的更新→API反映）・コメント投稿がDBまで正しく反映されることをE2Eで確認済みです。

## 既知の制限事項（Not in scope, v1）

- **認証・権限管理**: 全APIエンドポイントが認証不要（[ADR-0004](docs/adr/0004-no-auth.md)）
- **同時編集の競合制御**: バージョン採番・ステータス更新ともに楽観ロックを実装していない（要件定義書§16.6参照）
- **ドラッグ&ドロップ**: カンバンのステータス変更はセレクトボックスのみ対応。HTML5 Drag and Drop APIによる列間ドラッグは未実装（キーボード操作でも完結できることをアクセシビリティ上優先し、v1のスコープからは意図的に外した）
- **E2Eテストの自動実行範囲**: `frontend/e2e/kanban.spec.ts`はCI（`ci-frontend.yml`のe2e-testジョブ）で自動実行されるが、Docker Compose経由の統合起動そのものはCI化していない

## Design Decisions

- **DRYなCRUDファクトリ**: shots/assetsは同一スキーマのため、`backend/app/domain/items.py`の`create_item_router()`で共通化し、ルータファイル自体は1行で済ませている
- **VERSION/COMMENTのポリモーフィック関連**: DBレベルのFK制約を持たず、アプリ層で参照整合性を保証（[ADR-0002](docs/adr/0002-polymorphic-association.md)）
- **SQLiteを正本DBとして採用**: デモ規模のデータ量に対しPostgreSQL導入は過剰と判断（[ADR-0003](docs/adr/0003-sqlite.md)）
- **アップロードファイル名はUUID生成**: 元ファイル名をそのまま使わずパストラバーサル・衝突を防止（SEC-002）
- **拡張子とMIME typeの両方を検証**: なりすまし拡張子によるアップロード攻撃を防止（SEC-001）

## ライセンス

MIT License（[LICENSE](LICENSE)参照）
