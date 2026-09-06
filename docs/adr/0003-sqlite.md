# ADR-0003: SQLiteをv1の正本DBとして採用

## Status
Accepted (2026-09-07)

## Context
デモ規模（数百件程度）のデータ量で、個人開発・単一プロセスでの運用を想定している。

## Decision
PostgreSQL等のクライアント/サーバー型DBは導入せず、SQLiteファイル（`pipeboard.db`）を正本とする。

## Consequences
良い: 追加のミドルウェア・接続設定が不要で、`docker-compose up`だけで即座に動作する
悪い: 複数プロセスからの同時書き込みへの耐性が低い（`versions`の採番衝突は§8.2で許容と明記）

## Alternatives Considered
- PostgreSQL: 本番運用・複数ユーザー同時アクセスを想定する場合は妥当だが、v1のスコープ（個人開発・
  デモ規模）に対しては過剰投資と判断。将来スケールする場合の移行先として annex に記録する。
