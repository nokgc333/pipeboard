# ADR-0001: モノリポ・モジュラー構成の採用

## Status
Accepted (2026-09-07)

## Context
フロントエンド（Next.js）とバックエンド（FastAPI）を1つのポートフォリオ作品として管理する必要がある。

## Decision
`frontend/`・`backend/`・`scripts/`を1つのGitリポジトリ（モノレポ）で管理する。ただし各ディレクトリは
独立した依存関係管理（`frontend/package.json` / `backend/requirements.txt`）を持ち、CIも
`ci-frontend.yml` / `ci-backend.yml`に分離する（モジュラーモノリス的な構成）。

## Consequences
良い: 1つのPRでフロント・バック両方の変更を追跡でき、レビューが容易
悪い: 依存関係のバージョン管理がディレクトリごとに独立し、統一的なバージョン管理ツール（Nx等）は導入していない

## Alternatives Considered
- マルチレポ（frontend/backendを別リポジトリに分離）: 個人開発・小規模のため管理コストが見合わず却下
