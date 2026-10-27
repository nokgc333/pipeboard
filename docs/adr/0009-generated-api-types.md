# ADR-0009: フロントエンドの API の型は、OpenAPI から生成する

## Status
Accepted (2026-10-27)

## Context
フロントエンドの `api-client.ts` に、API の応答の型を手書きしていた。API を変えるたびに、手で追従する必要があり、食い違っても気づけなかった。

## Decision
- バックエンドが OpenAPI を書き出す(`python -m app.export_openapi`、`frontend/openapi.json`)。`ItemStatus` や `ItemType` は `Literal` にして、`enum` として公開する。
- `openapi-typescript` で `frontend/src/lib/api-types.ts` を生成し、DTO の型は、そこから取る。生成物は、リポジトリに入れる(差分が見える)。
- 古くなると CI が落ちる: バックエンドのテスト(`openapi.json` が実際の API と一致するか)と、フロントエンドの CI(再生成して差分がないか)。同じ仕組みで、API 一覧(`docs/api.md`)も生成する。

## Consequences
良い: API の変更が、型エラーとして、フロントエンドのコンパイルで見つかる。
悪い: API を変えたら、2 つの生成コマンドを実行する必要がある(忘れると CI が教える)。
      fetch の呼び出しそのものは、手書きの薄いラッパーのまま(完全なクライアント生成は、依存が増えるため見送り)。
