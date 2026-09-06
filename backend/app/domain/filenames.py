"""アップロードファイルの安全なファイル名生成（SEC-002）。"""

from __future__ import annotations

import uuid


def generate_safe_filename(original_filename: str, ext: str) -> str:
    """元のファイル名に依存しない安全なファイル名を生成する。

    パストラバーサル（'../../etc/passwd'等）やファイル名衝突を防ぐため、
    拡張子のみを呼び出し元から受け取り、本体はUUID4で生成する
    （original_filenameは将来の拡張時にログ等で使う可能性があるため引数として残すが、
    ファイル名の生成には一切使用しない）。
    """
    return f"{uuid.uuid4()}{ext}"
