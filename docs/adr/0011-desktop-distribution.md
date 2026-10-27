# ADR-0011: デスクトップクライアントの配布は、当面ソースからの実行にする

## Status
Accepted (2026-10-27)

## Context
PySide6 のデスクトップクライアントを、利用者に配るには、PyInstaller などで、OS ごとの実行ファイルにする方法がある。

## Decision
当面は、ソースから実行する(`python -m desktop_client.app`)ことのままにし、実行ファイルは作らない。

理由:
- 目的は、同じ API を叩く別の入口が作れることの実証で、配布が主題ではない
- PySide6 を含む実行ファイルは大きく(数百 MB)、OS ごとのビルド・署名・公証(macOS)・SmartScreen 対応(Windows)が要る
- 機能は、ショットの閲覧と変更に限っており、アーティストの日常の入口は Web と Houdini のスクリプト

## Consequences
配るとなったとき: PyInstaller の `--onedir` を、GitHub Actions のマトリクス(macOS・Windows)で作り、タグに添付する。署名の費用と手順を、そのとき決める。
