# Changelog

形式は [Keep a Changelog](https://keepachangelog.com/) に、版の付け方は [Semantic Versioning](https://semver.org/) に従う。

## [0.2.0] - 2026-10-27

### Added

- 認証(`local` / `token`)・ロール(viewer / editor / admin)・レート制限・セキュリティヘッダ
- 監査ログ(誰が・いつ・何を)と、署名つきの Webhook 通知
- 一覧の検索・絞り込み・ページング(`X-Total-Count`)
- 公開ゲート: 必須の検査(共通レポート形式)に通らないと、レビュー・完了に進めない
- プロジェクト > シーケンス > ショットの階層
- Houdini からのパブリッシュ(サムネイル・検査結果・ステータス)と、実機の検証記録
- PostgreSQL 対応(CI で検証)、SQLite は WAL
- Alembic によるマイグレーション、OpenAPI から生成するフロントエンドの型
- `/health`(データベースまで確認)、Docker のヘルスチェック、`.env.example`
- Web のスクリーンリーダー通知・Lighthouse の基準(CI)、デスクトップのキーボード操作

### Changed

- ステータス変更・コメント・アップロードは、存在しない対象を 404 で拒否する
- Docker イメージは、ハッシュつきの固定した依存で、非 root で動く

### Fixed

- 存在しない対象に付いたコメント・バージョンが作れてしまう問題

## [0.1.0]

- 最初の版: カンバン、ギャラリー、コメント、デスクトップクライアント、Houdini のステータス更新
