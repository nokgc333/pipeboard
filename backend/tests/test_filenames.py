"""domain/filenames.py の単体テスト（SEC-002: パストラバーサル・衝突防止）。"""

import re

from app.domain.filenames import generate_safe_filename

UUID4_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")


def test_generates_uuid_based_filename_with_original_extension() -> None:
    result = generate_safe_filename("my photo.jpg", ".jpg")

    stem, ext = result.rsplit(".", 1)
    assert ext == "jpg"
    assert UUID4_RE.match(stem)


def test_path_traversal_in_original_name_does_not_leak_into_result() -> None:
    result = generate_safe_filename("../../etc/passwd.png", ".png")

    assert "/" not in result
    assert ".." not in result


def test_two_calls_produce_different_filenames() -> None:
    a = generate_safe_filename("same.png", ".png")
    b = generate_safe_filename("same.png", ".png")

    assert a != b
