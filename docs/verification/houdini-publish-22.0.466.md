# Houdini 22.0.466(Indie)でのパブリッシュ検証

> 実施日: 2026-10-27
> 環境: macOS(Apple Silicon)/ Steam 版 Houdini Indie 22.0.466 の `hython`(Python 3.13、`requests` 同梱)
> 対象: `scripts/houdini_publish.py`(サムネイル生成 → アップロード → 検査結果の提出 → ステータス変更)

## 構成

- バックエンド: `PIPEBOARD_AUTH_MODE=token`、`PIPEBOARD_REQUIRED_CHECKS=unibridge`(公開ゲートを有効にして起動)
- 検査レポート: unibridge の `integrity-check --format json` の出力(合格)と、エラーを足した不合格版

## コマンド

```bash
PIPEBOARD_ITEM_ID=1 PIPEBOARD_API_TOKEN=<editor のトークン> \
PIPEBOARD_PASS_REPORT=pass.json PIPEBOARD_FAIL_REPORT=fail.json \
hython scripts/verify_houdini_publish.py
```

## 結果(全 5 項目 PASS)

```text
thumbnail_is_written_as_png PASS 739 bytes
gate_blocks_a_failed_check PASS Failed checks: unibridge
version_is_uploaded PASS 2
passing_check_is_accepted PASS
status_moves_to_review_after_the_gate_passes PASS
```

## サーバー側で確認したこと

- ショットのステータスが `in_review` になった
- 検査結果が 2 件(不合格 → 合格)、バージョンが 2 件(不合格のときもアップロードは済んでいる)
- 監査ログに、`shot.create` / `version.upload` / `shot.check` / `shot.status` が、操作者 `editor` で残った

## 観察

- 不合格のレポートで `in_review` へ進めようとすると、公開ゲートが 409(`Failed checks: unibridge`)で止める。同じ検査が合格すれば通る
- サムネイルは COP2 の単色画像で、GL を使わない。実際のシーンの見た目を使うときは、ビューポートやレンダーの出力ファイルを `publish` に渡す(この記録の対象外)
- 出力が終わっても `hython` が終了しないことがある。結果が出たあとに、手で止めてよい
