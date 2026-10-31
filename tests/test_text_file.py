import os
from pathlib import Path

import pytest

from fsg.errors import FileError
from fsg.text_file import TextFile


class TestNewline:
    """Covers detecting the line break style."""

    @pytest.mark.parametrize(("text", "expected"), [("a\nb", "\n"), ("a\r\nb", "\r\n"), ("", "\n")])
    def test_detects_style(self, text: str, expected: str) -> None:
        """Returns CRLF only when the text contains it."""

        assert TextFile.newline(text) == expected


class TestRead:
    """Covers reading the file."""

    def test_keeps_line_endings(self, tmp_path: Path) -> None:
        """Returns CRLF line endings untranslated."""

        (tmp_path / "a.md").write_bytes(b"a\r\nb\n")
        assert TextFile(tmp_path / "a.md").read() == "a\r\nb\n"

    def test_rejects_missing_file(self, tmp_path: Path) -> None:
        """Raises ValueError when the file does not exist."""

        with pytest.raises(FileError, match="file not found"):
            TextFile(tmp_path / "a.md").read()

    def test_rejects_non_utf8_file(self, tmp_path: Path) -> None:
        """Raises ValueError when the content is not valid UTF-8."""

        (tmp_path / "a.md").write_bytes(b"\xff")
        with pytest.raises(FileError, match="UTF-8"):
            TextFile(tmp_path / "a.md").read()


class TestWrite:
    """Covers replacing the file."""

    def test_writes_text_without_translation(self, tmp_path: Path) -> None:
        """Writes the exact characters, including CRLF line endings."""

        TextFile(tmp_path / "a.md").write("a\r\nb\n")
        assert (tmp_path / "a.md").read_bytes() == b"a\r\nb\n"

    def test_replaces_existing_content(self, tmp_path: Path) -> None:
        """Overwrites the previous content completely."""

        (tmp_path / "a.md").write_text("old content", encoding="utf-8")
        TextFile(tmp_path / "a.md").write("new")
        assert (tmp_path / "a.md").read_text(encoding="utf-8") == "new"

    def test_leaves_no_temporary_file(self, tmp_path: Path) -> None:
        """Removes nothing but the target from the directory after writing."""

        TextFile(tmp_path / "a.md").write("x")
        assert [path.name for path in tmp_path.iterdir()] == ["a.md"]

    def test_keeps_original_on_failure(self, tmp_path: Path, monkeypatch) -> None:
        """Leaves the original file and no temporary file behind when replacing fails."""

        (tmp_path / "a.md").write_text("original", encoding="utf-8")

        def fail(*_: object) -> None:
            raise OSError("disk full")

        monkeypatch.setattr("os.replace", fail)
        with pytest.raises(FileError, match="disk full"):
            TextFile(tmp_path / "a.md").write("new")
        assert (tmp_path / "a.md").read_text(encoding="utf-8") == "original"
        assert [path.name for path in tmp_path.iterdir()] == ["a.md"]

    @pytest.mark.skipif(os.name != "posix", reason="permission bits are POSIX only")
    def test_keeps_permissions(self, tmp_path: Path) -> None:
        """Keeps the permission bits of an existing file."""

        (tmp_path / "a.md").write_text("x", encoding="utf-8")
        (tmp_path / "a.md").chmod(0o640)
        TextFile(tmp_path / "a.md").write("y")
        assert (tmp_path / "a.md").stat().st_mode & 0o777 == 0o640

    @pytest.mark.skipif(os.name != "posix", reason="permission bits are POSIX only")
    def test_applies_mode_to_new_file(self, tmp_path: Path) -> None:
        """Gives a new file the requested permission bits."""

        TextFile(tmp_path / "hook").write("x", mode=0o755)
        assert (tmp_path / "hook").stat().st_mode & 0o777 == 0o755

    def test_writes_through_symlink(self, tmp_path: Path) -> None:
        """Updates the link target and keeps the symlink in place."""

        (tmp_path / "real.md").write_text("old", encoding="utf-8")
        try:
            (tmp_path / "link.md").symlink_to(tmp_path / "real.md")
        except OSError:
            pytest.skip("creating symlinks is not permitted")
        TextFile(tmp_path / "link.md").write("new")
        assert (tmp_path / "link.md").is_symlink()
        assert (tmp_path / "real.md").read_text(encoding="utf-8") == "new"