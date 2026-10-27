"""houdini_publish.py の単体テスト(HTTP 呼び出しは偽のセッション、hou は偽のモジュール)。"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from houdini_publish import (  # noqa: E402
    PublishBlocked,
    PublishError,
    load_check_report,
    publish,
    publish_version,
    submit_check,
    write_cop_thumbnail,
)

BASE = "http://localhost:8000"
REPORT: dict[str, Any] = {
    "schema_version": "1",
    "tool": "unibridge",
    "generated_at": "2026-10-27T01:02:03+00:00",
    "subject": "scene.usda",
    "has_errors": False,
    "findings": [],
}


def _response(status: int, body: Any) -> MagicMock:
    response = MagicMock()
    response.status_code = status
    response.ok = status < 400
    response.json.return_value = body
    response.raise_for_status.side_effect = None if status < 400 else RuntimeError(f"HTTP {status}")
    return response


def _image(tmp_path: Path, name: str = "thumb.png") -> Path:
    path = tmp_path / name
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 16)
    return path


class TestPublishVersion:
    def test_uploads_the_image_to_the_versions_endpoint_with_item_in_the_query(
        self, tmp_path: Path
    ) -> None:
        session = MagicMock()
        session.post.return_value = _response(201, {"id": 1, "version_number": 1})

        result = publish_version(BASE, "shot", 12, _image(tmp_path), session=session)

        url = session.post.call_args.args[0]
        assert url == f"{BASE}/versions?item_type=shot&item_id=12"
        name, _, mime = session.post.call_args.kwargs["files"]["file"]
        assert (name, mime) == ("thumb.png", "image/png")
        assert result["version_number"] == 1

    @pytest.mark.parametrize(
        ("filename", "mime"),
        [("a.jpg", "image/jpeg"), ("a.JPEG", "image/jpeg"), ("a.webp", "image/webp")],
    )
    def test_the_mime_type_follows_the_extension(
        self, tmp_path: Path, filename: str, mime: str
    ) -> None:
        session = MagicMock()
        session.post.return_value = _response(201, {})

        publish_version(BASE, "asset", 1, _image(tmp_path, filename), session=session)

        assert session.post.call_args.kwargs["files"]["file"][2] == mime

    def test_an_unsupported_extension_is_refused_before_any_request(self, tmp_path: Path) -> None:
        session = MagicMock()

        with pytest.raises(ValueError, match="png, jpg, jpeg or webp"):
            publish_version(BASE, "shot", 1, _image(tmp_path, "scene.exr"), session=session)

        session.post.assert_not_called()

    def test_a_missing_file_is_reported(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            publish_version(BASE, "shot", 1, tmp_path / "none.png", session=MagicMock())

    def test_the_token_is_sent_as_a_bearer_header(self, tmp_path: Path) -> None:
        session = MagicMock()
        session.post.return_value = _response(201, {})

        publish_version(
            BASE, "shot", 1, _image(tmp_path), session=session, token="tok-123456789012"
        )

        assert session.post.call_args.kwargs["headers"] == {
            "Authorization": "Bearer tok-123456789012"
        }

    def test_the_token_falls_back_to_the_environment(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("PIPEBOARD_API_TOKEN", "env-token-123456")
        session = MagicMock()
        session.post.return_value = _response(201, {})

        publish_version(BASE, "shot", 1, _image(tmp_path), session=session)

        assert (
            session.post.call_args.kwargs["headers"]["Authorization"] == "Bearer env-token-123456"
        )

    def test_a_server_error_raises_a_publish_error_with_the_status(self, tmp_path: Path) -> None:
        session = MagicMock()
        session.post.return_value = _response(404, {"title": "Shot 9 not found"})

        with pytest.raises(PublishError, match="404.*Shot 9 not found"):
            publish_version(BASE, "shot", 9, _image(tmp_path), session=session)


class TestSubmitCheck:
    def test_posts_the_report_as_json(self) -> None:
        session = MagicMock()
        session.post.return_value = _response(201, {"passed": True})

        result = submit_check(BASE, "asset", 3, REPORT, session=session)

        assert session.post.call_args.args[0] == f"{BASE}/assets/3/checks"
        assert session.post.call_args.kwargs["json"] == REPORT
        assert result == {"passed": True}


class TestLoadCheckReport:
    def test_reads_a_report_in_the_shared_format(self, tmp_path: Path) -> None:
        path = tmp_path / "report.json"
        path.write_text(json.dumps(REPORT), encoding="utf-8")

        assert load_check_report(path) == REPORT

    @pytest.mark.parametrize("missing", ["tool", "has_errors", "findings", "schema_version"])
    def test_a_report_without_a_required_key_is_refused(self, tmp_path: Path, missing: str) -> None:
        broken = {k: v for k, v in REPORT.items() if k != missing}
        path = tmp_path / "report.json"
        path.write_text(json.dumps(broken), encoding="utf-8")

        with pytest.raises(ValueError, match=missing):
            load_check_report(path)

    def test_text_that_is_not_json_is_refused(self, tmp_path: Path) -> None:
        path = tmp_path / "report.json"
        path.write_text("not json", encoding="utf-8")

        with pytest.raises(ValueError, match="not valid JSON"):
            load_check_report(path)


class TestPublish:
    def test_uploads_then_submits_the_check_then_changes_the_status(self, tmp_path: Path) -> None:
        session = MagicMock()
        session.post.side_effect = [
            _response(201, {"id": 1, "version_number": 2}),
            _response(201, {"id": 5, "passed": True}),
        ]
        session.patch.return_value = _response(200, {"status": "in_review"})
        report = tmp_path / "r.json"
        report.write_text(json.dumps(REPORT), encoding="utf-8")

        result = publish(
            BASE,
            "shot",
            12,
            _image(tmp_path),
            report_path=report,
            status="in_review",
            session=session,
        )

        assert [c.args[0] for c in session.post.call_args_list] == [
            f"{BASE}/versions?item_type=shot&item_id=12",
            f"{BASE}/shots/12/checks",
        ]
        assert session.patch.call_args.args[0] == f"{BASE}/shots/12/status"
        assert result["version"]["version_number"] == 2
        assert result["check"]["passed"] is True
        assert result["status"] == "in_review"

    def test_without_a_report_or_status_only_the_image_is_uploaded(self, tmp_path: Path) -> None:
        session = MagicMock()
        session.post.return_value = _response(201, {"version_number": 1})

        result = publish(BASE, "shot", 1, _image(tmp_path), session=session)

        assert session.post.call_count == 1
        session.patch.assert_not_called()
        assert result["check"] is None
        assert result["status"] is None

    def test_a_blocked_gate_raises_with_the_reason_and_keeps_what_was_already_sent(
        self, tmp_path: Path
    ) -> None:
        session = MagicMock()
        session.post.return_value = _response(201, {"version_number": 1})
        blocked = _response(409, {"title": "Failed checks: unibridge"})
        session.patch.return_value = blocked

        with pytest.raises(PublishBlocked, match="Failed checks: unibridge"):
            publish(BASE, "shot", 1, _image(tmp_path), status="done", session=session)

    def test_an_invalid_report_stops_before_the_upload(self, tmp_path: Path) -> None:
        session = MagicMock()
        report = tmp_path / "r.json"
        report.write_text("{}", encoding="utf-8")

        with pytest.raises(ValueError):
            publish(BASE, "shot", 1, _image(tmp_path), report_path=report, session=session)

        session.post.assert_not_called()


class TestWriteCopThumbnail:
    def _fake_hou(self) -> tuple[MagicMock, MagicMock, MagicMock, MagicMock]:
        hou = MagicMock()
        network = MagicMock()
        color = MagicMock()
        rop = MagicMock()
        color.path.return_value = "/img/img1/color1"
        hou.node.return_value.createNode.return_value = network
        network.createNode.side_effect = [color, rop]
        return hou, network, color, rop

    @staticmethod
    def _values(node: MagicMock) -> dict[str, Any]:
        return {
            c.args[0]: node.parm.return_value.set.call_args_list for c in node.parm.call_args_list
        }

    def test_builds_a_color_to_rop_network_inside_the_compositing_context(
        self, tmp_path: Path
    ) -> None:
        hou, network, _, _ = self._fake_hou()

        write_cop_thumbnail(hou, tmp_path / "t.png")

        hou.node.assert_called_once_with("/img")
        hou.node.return_value.createNode.assert_called_once_with("img")
        assert [c.args[0] for c in network.createNode.call_args_list] == ["color", "rop_comp"]

    def test_the_color_node_gets_the_size_and_the_color(self, tmp_path: Path) -> None:
        hou, _, color, _ = self._fake_hou()

        write_cop_thumbnail(hou, tmp_path / "t.png", width=320, height=180, color=(0.1, 0.2, 0.3))

        parms = {c.args[0] for c in color.parm.call_args_list}
        assert {"overridesize", "size1", "size2", "colorr", "colorg", "colorb"} <= parms
        sets = [c.args[0] for c in color.parm.return_value.set.call_args_list]
        assert sets == [1, 320, 180, 0.1, 0.2, 0.3]

    def test_the_rop_reads_the_color_node_and_writes_the_path(self, tmp_path: Path) -> None:
        hou, _, _, rop = self._fake_hou()
        out = tmp_path / "t.png"

        write_cop_thumbnail(hou, out)

        sets = [c.args[0] for c in rop.parm.return_value.set.call_args_list]
        assert "/img/img1/color1" in sets
        assert str(out) in sets
        rop.parm.return_value.pressButton.assert_called_once()

    def test_the_output_folder_is_created(self, tmp_path: Path) -> None:
        hou, _, _, _ = self._fake_hou()

        write_cop_thumbnail(hou, tmp_path / "new" / "dir" / "t.png")

        assert (tmp_path / "new" / "dir").is_dir()

    def test_the_temporary_network_is_always_destroyed(self, tmp_path: Path) -> None:
        hou, network, _, rop = self._fake_hou()
        rop.parm.return_value.pressButton.side_effect = RuntimeError("render failed")

        with pytest.raises(RuntimeError, match="render failed"):
            write_cop_thumbnail(hou, tmp_path / "t.png")

        network.destroy.assert_called_once()

    def test_an_unsupported_extension_is_refused_before_touching_houdini(
        self, tmp_path: Path
    ) -> None:
        hou = MagicMock()

        with pytest.raises(ValueError, match="png, jpg, jpeg or webp"):
            write_cop_thumbnail(hou, tmp_path / "t.exr")

        hou.node.assert_not_called()
