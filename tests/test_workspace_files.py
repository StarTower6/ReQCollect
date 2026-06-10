"""Tests for WorkspaceFileManager and workspace file tools."""

import json
import tempfile
from pathlib import Path

import pytest

from app.core.file_handler import FileValidationError
from app.core.workspace_files import WorkspaceFileManager


@pytest.fixture
def tmp_ws_id() -> str:
    return "test-ws-001"


@pytest.fixture(autouse=True)
def patch_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Point config.data_dir to a temp dir."""
    monkeypatch.setattr("app.config.config.data_dir", str(tmp_path))
    return tmp_path


class TestWorkspaceFileManager:
    def test_list_empty(self, tmp_ws_id: str):
        fm = WorkspaceFileManager(tmp_ws_id)
        assert fm.list_files() == []

    def test_upload_and_list(self, tmp_ws_id: str):
        fm = WorkspaceFileManager(tmp_ws_id)
        result = fm.upload_file("test.md", b"# Hello\nThis is a test.", "user1")
        assert result["path"] == "test.md"
        assert result["type"] == "md"

        files = fm.list_files()
        assert len(files) == 1
        assert files[0]["path"] == "test.md"
        assert files[0]["source"] == "upload"

    def test_upload_and_read(self, tmp_ws_id: str):
        fm = WorkspaceFileManager(tmp_ws_id)
        fm.upload_file("readme.md", b"# Readme\nContent here.", "user1")
        content = fm.read_file("readme.md")
        assert "Readme" in content["text"]
        assert content["type"] == "md"
        assert not content["truncated"]

    def test_read_truncated(self, tmp_ws_id: str):
        fm = WorkspaceFileManager(tmp_ws_id)
        long_text = "x" * 10000
        fm.upload_file("long.txt", long_text.encode(), "user1")
        content = fm.read_file("long.txt", max_chars=100)
        assert content["truncated"]
        assert len(content["text"]) == 100

    def test_read_file_section(self, tmp_ws_id: str):
        fm = WorkspaceFileManager(tmp_ws_id)
        lines = "\n".join(f"line {i}" for i in range(1, 101))
        fm.upload_file("lines.txt", lines.encode(), "user1")
        result = fm.read_file_section("lines.txt", 10, 20)
        assert result["start_line"] == 10
        assert result["end_line"] == 20
        assert len(result["lines"]) == 11
        assert "line 10" in result["lines"][0]

    def test_search(self, tmp_ws_id: str):
        fm = WorkspaceFileManager(tmp_ws_id)
        fm.upload_file("a.md", b"# Project Alpha\nRequirement: login", "user1")
        fm.upload_file("b.md", b"# Project Beta\nRequirement: export", "user1")

        results = fm.search_files("login")
        assert len(results) == 1
        assert results[0]["path"] == "a.md"

    def test_search_across_files(self, tmp_ws_id: str):
        fm = WorkspaceFileManager(tmp_ws_id)
        fm.upload_file("a.md", b"Alpha content", "user1")
        fm.upload_file("b.md", b"Beta also has content", "user1")

        results = fm.search_files("content")
        assert len(results) >= 1

    def test_search_respects_pattern(self, tmp_ws_id: str):
        fm = WorkspaceFileManager(tmp_ws_id)
        fm.upload_file("a.md", b"keyword in md", "user1")
        fm.upload_file("b.txt", b"keyword in txt", "user1")

        results = fm.search_files("keyword", file_pattern="*.md")
        assert len(results) == 1
        assert results[0]["path"] == "a.md"

    def test_write_file(self, tmp_ws_id: str):
        fm = WorkspaceFileManager(tmp_ws_id)
        result = fm.write_file("report.md", "# Analysis Report\n\nDone.")
        assert result["path"] == "report.md"

        content = fm.read_file("report.md")
        assert "Analysis Report" in content["text"]

    def test_write_updates_index(self, tmp_ws_id: str):
        fm = WorkspaceFileManager(tmp_ws_id)
        fm.write_file("output.md", "# Output")
        info = fm.get_info()
        assert info["file_count"] == 1
        assert info["by_source"].get("generated", 0) == 1

    def test_delete_file(self, tmp_ws_id: str):
        fm = WorkspaceFileManager(tmp_ws_id)
        fm.upload_file("todelete.md", b"Delete me", "user1")
        assert len(fm.list_files()) == 1
        fm.delete_file("todelete.md")
        assert len(fm.list_files()) == 0

    def test_delete_nonexistent(self, tmp_ws_id: str):
        fm = WorkspaceFileManager(tmp_ws_id)
        assert not fm.delete_file("nonexistent.md")

    def test_get_file_info(self, tmp_ws_id: str):
        fm = WorkspaceFileManager(tmp_ws_id)
        fm.upload_file("info.md", b"# Info", "user1")
        info = fm.get_file_info("info.md")
        assert info is not None
        assert info["path"] == "info.md"

    def test_get_file_info_missing(self, tmp_ws_id: str):
        fm = WorkspaceFileManager(tmp_ws_id)
        assert fm.get_file_info("missing.md") is None

    def test_get_info_empty(self, tmp_ws_id: str):
        fm = WorkspaceFileManager(tmp_ws_id)
        info = fm.get_info()
        assert info["file_count"] == 0
        assert info["by_type"] == {}
        assert info["by_source"] == {}

    def test_get_info_with_files(self, tmp_ws_id: str):
        fm = WorkspaceFileManager(tmp_ws_id)
        fm.upload_file("a.md", b"a", "user1")
        fm.upload_file("b.md", b"b", "user1")
        fm.write_file("c.md", "c")
        info = fm.get_info()
        assert info["file_count"] == 3
        assert info["by_type"].get("md", 0) == 3

    def test_upload_invalid_type(self, tmp_ws_id: str):
        fm = WorkspaceFileManager(tmp_ws_id)
        with pytest.raises(FileValidationError):
            fm.upload_file("bad.exe", b"nope", "user1")

    def test_read_nonexistent(self, tmp_ws_id: str):
        fm = WorkspaceFileManager(tmp_ws_id)
        with pytest.raises(FileNotFoundError):
            fm.read_file("nope.md")

    def test_filter_by_pattern(self, tmp_ws_id: str):
        fm = WorkspaceFileManager(tmp_ws_id)
        fm.upload_file("readme.md", b"# R", "user1")
        fm.upload_file("notes.txt", b"notes", "user1")
        fm.upload_file("data.json", b"{}", "user1")

        mds = fm.list_files(pattern="*.md")
        assert len(mds) == 1
        assert mds[0]["type"] == "md"

    def test_list_respects_max_results(self, tmp_ws_id: str):
        fm = WorkspaceFileManager(tmp_ws_id)
        for i in range(5):
            fm.upload_file(f"f{i}.md", f"file {i}".encode(), "user1")
        assert len(fm.list_files(max_results=2)) == 2

    def test_upload_deduplicate(self, tmp_ws_id: str):
        fm = WorkspaceFileManager(tmp_ws_id)
        fm.upload_file("same.md", b"same content", "user1")
        fm.upload_file("same.md", b"same content", "user1")
        assert len(fm.list_files()) == 1

    def test_path_traversal_rejected(self):
        from app.core.workspace_files import _validate_file_path
        from app.core.file_handler import FileValidationError
        with pytest.raises(FileValidationError):
            _validate_file_path(Path("/tmp"), "../../etc/passwd")
