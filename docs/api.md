# API 一覧

`python -m app.export_api_doc ../docs/api.md` で、実際の API から生成する(手で編集しない。
テストが、実際の API と一致していることを確かめる)。完全な定義は、起動中の `/docs`(Swagger UI)と
`frontend/openapi.json` にある。

ロールは、必要な最小の権限。`token` モードで、未認証は 401、権限不足は 403。
`local` モードでは、すべて管理者として扱う。


## assets

| メソッド | パス | ロール | 概要 |
| --- | --- | --- | --- |
| GET | `/assets` | viewer | list items |
| POST | `/assets` | editor | create item |
| GET | `/assets/{item_id}` | viewer | get item |
| PUT | `/assets/{item_id}` | editor | update item |
| DELETE | `/assets/{item_id}` | admin | delete item |
| GET | `/assets/{item_id}/checks` | viewer | list checks |
| POST | `/assets/{item_id}/checks` | editor | submit check |
| GET | `/assets/{item_id}/comments` | viewer | list comments |
| PATCH | `/assets/{item_id}/status` | editor | update status |
| GET | `/assets/{item_id}/versions` | viewer | list versions |

## audit

| メソッド | パス | ロール | 概要 |
| --- | --- | --- | --- |
| GET | `/audit-log` | admin | list audit log |

## comments

| メソッド | パス | ロール | 概要 |
| --- | --- | --- | --- |
| POST | `/comments` | editor | create comment |

## health

| メソッド | パス | ロール | 概要 |
| --- | --- | --- | --- |
| GET | `/health` | なし | health |
| GET | `/healthz` | なし | healthz |

## projects

| メソッド | パス | ロール | 概要 |
| --- | --- | --- | --- |
| GET | `/projects` | viewer | list projects |
| POST | `/projects` | editor | create project |
| DELETE | `/projects/{project_id}` | admin | delete project |
| GET | `/projects/{project_id}/sequences` | viewer | list sequences |
| POST | `/projects/{project_id}/sequences` | editor | create sequence |
| DELETE | `/sequences/{sequence_id}` | admin | delete sequence |

## shots

| メソッド | パス | ロール | 概要 |
| --- | --- | --- | --- |
| GET | `/shots` | viewer | list items |
| POST | `/shots` | editor | create item |
| GET | `/shots/{item_id}` | viewer | get item |
| PUT | `/shots/{item_id}` | editor | update item |
| DELETE | `/shots/{item_id}` | admin | delete item |
| GET | `/shots/{item_id}/checks` | viewer | list checks |
| POST | `/shots/{item_id}/checks` | editor | submit check |
| GET | `/shots/{item_id}/comments` | viewer | list comments |
| PUT | `/shots/{item_id}/sequence` | editor | assign sequence |
| PATCH | `/shots/{item_id}/status` | editor | update status |
| GET | `/shots/{item_id}/versions` | viewer | list versions |

## uploads

| メソッド | パス | ロール | 概要 |
| --- | --- | --- | --- |
| GET | `/uploads/{filename}` | なし | get upload |

## versions

| メソッド | パス | ロール | 概要 |
| --- | --- | --- | --- |
| POST | `/versions` | editor | upload version |
