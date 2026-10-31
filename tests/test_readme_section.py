from pathlib import Path

import pytest

from fsg.readme_section import END_MARKER, START_MARKER, ReadmeSection


def write_readme(path: Path, text: str) -> Path:
    """Writes the text to README.md below the given directory without newline translation and returns its path.

    Args:
        path: Directory the file is created in.
        text: Exact file content.
    """

    readme = path / "README.md"
    with readme.open("w", encoding="utf-8", newline="") as file:
        file.write(text)
    return readme


def read_raw(path: Path) -> str:
    """Returns the file content without newline translation.

    Args:
        path: File to read.
    """

    with path.open(encoding="utf-8", newline="") as file:
        return file.read()


class TestInit:
    """Covers reading the file and locating the markers."""

    def test_reads_content_between_markers(self, tmp_path: Path) -> None:
        """Returns the exact text between the start and end marker."""

        readme = write_readme(tmp_path, f"# Title\n{START_MARKER}\nold\n{END_MARKER}\nrest\n")
        assert ReadmeSection(readme).content() == "\nold\n"

    def test_rejects_missing_start_marker(self, tmp_path: Path) -> None:
        """Raises ValueError when the start marker is missing."""

        readme = write_readme(tmp_path, f"# Title\n{END_MARKER}\n")
        with pytest.raises(ValueError, match="missing"):
            ReadmeSection(readme)

    def test_rejects_missing_end_marker(self, tmp_path: Path) -> None:
        """Raises ValueError when the end marker is missing."""

        readme = write_readme(tmp_path, f"# Title\n{START_MARKER}\n")
        with pytest.raises(ValueError, match="missing"):
            ReadmeSection(readme)

    def test_rejects_end_marker_before_start_marker(self, tmp_path: Path) -> None:
        """Raises ValueError when the end marker only appears before the start marker."""

        readme = write_readme(tmp_path, f"{END_MARKER}\n{START_MARKER}\n")
        with pytest.raises(ValueError, match="missing"):
            ReadmeSection(readme)

    def test_rejects_missing_file(self, tmp_path: Path) -> None:
        """Raises ValueError when the file does not exist."""

        with pytest.raises(ValueError, match="file not found"):
            ReadmeSection(tmp_path / "README.md")

    def test_rejects_non_utf8_file(self, tmp_path: Path) -> None:
        """Raises ValueError when the file is not valid UTF-8."""

        (tmp_path / "README.md").write_bytes(b"\xff\xfe\x00")
        with pytest.raises(ValueError, match="UTF-8"):
            ReadmeSection(tmp_path / "README.md")

    def test_names_missing_end_marker(self, tmp_path: Path) -> None:
        """Reports the end marker as missing when only the start marker exists."""

        readme = write_readme(tmp_path, f"{START_MARKER}\ntree\n")
        with pytest.raises(ValueError, match="fsg:end"):
            ReadmeSection(readme)

    def test_ignores_end_marker_inside_later_code_fence(self, tmp_path: Path) -> None:
        """Refuses the file instead of using an end marker from an example block when the real one is missing."""

        text = f"{START_MARKER}\n\n## Keep\ntext\n\n```markdown\n{START_MARKER}\n{END_MARKER}\n```\n"
        readme = write_readme(tmp_path, text)
        with pytest.raises(ValueError, match="fsg:end"):
            ReadmeSection(readme)
        assert read_raw(readme) == text

    def test_ignores_inline_end_marker(self, tmp_path: Path) -> None:
        """Skips an end marker that shares its line with other text."""

        text = f"{START_MARKER}\ntree\nSee `{END_MARKER}` below.\n{END_MARKER}\n"
        readme = write_readme(tmp_path, text)
        assert ReadmeSection(readme).content() == f"\ntree\nSee `{END_MARKER}` below.\n"

    def test_finds_end_marker_after_rendered_fence(self, tmp_path: Path) -> None:
        """Finds the end marker that follows a fenced tree written by fsg."""

        readme = write_readme(tmp_path, f"{START_MARKER}\n```plaintext\nroot/\n```\n{END_MARKER}\n")
        assert ReadmeSection(readme).content() == "\n```plaintext\nroot/\n```\n"

    def test_skips_markers_inside_code_fence(self, tmp_path: Path) -> None:
        """Ignores markers shown inside a backtick fence and uses the pair that follows it."""

        text = f"```markdown\n{START_MARKER}\n{END_MARKER}\n```\n\n{START_MARKER}\nreal\n{END_MARKER}\n"
        readme = write_readme(tmp_path, text)
        assert ReadmeSection(readme).content() == "\nreal\n"

    def test_skips_markers_inside_tilde_fence(self, tmp_path: Path) -> None:
        """Ignores markers shown inside a tilde fence."""

        readme = write_readme(tmp_path, f"~~~\n{START_MARKER}\n~~~\n{START_MARKER}\nreal\n{END_MARKER}\n")
        assert ReadmeSection(readme).content() == "\nreal\n"

    def test_rejects_markers_only_inside_code_fence(self, tmp_path: Path) -> None:
        """Raises ValueError when the only markers stand inside a code fence."""

        readme = write_readme(tmp_path, f"```\n{START_MARKER}\n{END_MARKER}\n```\n")
        with pytest.raises(ValueError, match="missing"):
            ReadmeSection(readme)

    def test_skips_inline_start_marker(self, tmp_path: Path) -> None:
        """Ignores a start marker that shares its line with other text."""

        text = f"Put `{START_MARKER}` in your file.\n{START_MARKER}\nreal\n{END_MARKER}\n"
        readme = write_readme(tmp_path, text)
        assert ReadmeSection(readme).content() == "\nreal\n"

    def test_accepts_indented_start_marker(self, tmp_path: Path) -> None:
        """Finds a start marker surrounded by whitespace on its own line."""

        readme = write_readme(tmp_path, f"  {START_MARKER}  \nreal\n{END_MARKER}\n")
        assert ReadmeSection(readme).content() == "  \nreal\n"


class TestIsCurrent:
    """Covers comparing the section with a tree."""

    def test_reports_matching_tree(self, tmp_path: Path) -> None:
        """Returns True when the section holds exactly the tree on its own lines."""

        readme = write_readme(tmp_path, f"{START_MARKER}\ntree\nlines\n{END_MARKER}\n")
        assert ReadmeSection(readme).is_current("tree\nlines") is True

    def test_reports_different_tree(self, tmp_path: Path) -> None:
        """Returns False when the section holds another tree."""

        readme = write_readme(tmp_path, f"{START_MARKER}\nold\n{END_MARKER}\n")
        assert ReadmeSection(readme).is_current("new") is False

    def test_reports_empty_section(self, tmp_path: Path) -> None:
        """Returns False when the markers enclose nothing."""

        readme = write_readme(tmp_path, f"{START_MARKER}\n{END_MARKER}\n")
        assert ReadmeSection(readme).is_current("tree") is False


class TestUpdate:
    """Covers writing the tree into the section."""

    def test_replaces_section_and_keeps_surrounding_text(self, tmp_path: Path) -> None:
        """Writes the tree between the markers and leaves the text around them untouched."""

        readme = write_readme(tmp_path, f"# Title\n\n{START_MARKER}\nold\n{END_MARKER}\n\n## Next\n")
        assert ReadmeSection(readme).update("new\ntree") is True
        assert read_raw(readme) == f"# Title\n\n{START_MARKER}\nnew\ntree\n{END_MARKER}\n\n## Next\n"

    def test_fills_empty_section(self, tmp_path: Path) -> None:
        """Puts the tree on its own lines when the markers enclose nothing."""

        readme = write_readme(tmp_path, f"{START_MARKER}\n{END_MARKER}")
        ReadmeSection(readme).update("tree")
        assert read_raw(readme) == f"{START_MARKER}\ntree\n{END_MARKER}"

    def test_leaves_current_file_untouched(self, tmp_path: Path) -> None:
        """Returns False and does not rewrite the file when the tree is already current."""

        readme = write_readme(tmp_path, f"{START_MARKER}\ntree\n{END_MARKER}\n")
        modified = readme.stat().st_mtime_ns
        assert ReadmeSection(readme).update("tree") is False
        assert readme.stat().st_mtime_ns == modified

    def test_keeps_crlf_line_endings(self, tmp_path: Path) -> None:
        """Writes the tree with CRLF line breaks when the file uses CRLF."""

        readme = write_readme(tmp_path, f"# Title\r\n{START_MARKER}\r\nold\r\n{END_MARKER}\r\n")
        ReadmeSection(readme).update("new\ntree")
        assert read_raw(readme) == f"# Title\r\n{START_MARKER}\r\nnew\r\ntree\r\n{END_MARKER}\r\n"

    def test_is_current_after_update(self, tmp_path: Path) -> None:
        """Reports the written tree as current on the same object and on a fresh read."""

        readme = write_readme(tmp_path, f"{START_MARKER}\nold\n{END_MARKER}\n")
        section = ReadmeSection(readme)
        section.update("new")
        assert section.is_current("new") is True
        assert ReadmeSection(readme).is_current("new") is True

    def test_updates_only_first_section(self, tmp_path: Path) -> None:
        """Replaces the first marked section and keeps any later one."""

        text = f"{START_MARKER}\na\n{END_MARKER}\n{START_MARKER}\nb\n{END_MARKER}\n"
        readme = write_readme(tmp_path, text)
        ReadmeSection(readme).update("x")
        assert read_raw(readme) == f"{START_MARKER}\nx\n{END_MARKER}\n{START_MARKER}\nb\n{END_MARKER}\n"