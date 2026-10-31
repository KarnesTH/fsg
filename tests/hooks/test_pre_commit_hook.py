from importlib.metadata import version
from pathlib import Path

import pytest

from fsg.errors import HookError
from fsg.hooks import PreCommitHook

VERSION = version("fsg")


def entry(indent: str, target: str = "README.md") -> str:
    """Returns the expected fsg list item with the given indentation.

    Args:
        indent: Whitespace before the list dash.
        target: Target as written into the args list.
    """

    return (
        f"{indent}- repo: https://github.com/KarnesTH/fsg\n"
        f"{indent}  rev: v{VERSION}\n"
        f"{indent}  hooks:\n"
        f"{indent}    - id: fsg\n"
        f"{indent}      args: [--update, {target}]\n"
    )


def install(tmp_path: Path, text: str, target: str = "README.md") -> str:
    """Writes the config text, installs the hook and returns the resulting file content.

    Args:
        tmp_path: Repository directory.
        text: Initial content of .pre-commit-config.yaml.
        target: Target file passed to the hook.
    """

    config = tmp_path / ".pre-commit-config.yaml"
    with config.open("w", encoding="utf-8", newline="") as file:
        file.write(text)
    assert PreCommitHook(tmp_path, target).install() is True
    with config.open(encoding="utf-8", newline="") as file:
        return file.read()


class TestInstall:
    """Covers appending the fsg entry to an existing config."""

    def test_appends_to_indented_list(self, tmp_path: Path) -> None:
        """Adds the entry after the last item using the indentation of the existing items."""

        text = "repos:\n  - repo: https://example.com/a\n    rev: v1\n    hooks:\n      - id: a\n"
        assert install(tmp_path, text) == text + entry("  ")

    def test_appends_to_unindented_list(self, tmp_path: Path) -> None:
        """Keeps list items at column zero when the file uses that style."""

        text = "repos:\n- repo: https://example.com/a\n  rev: v1\n  hooks:\n  - id: a\n"
        assert install(tmp_path, text) == text + entry("")

    def test_inserts_before_following_top_level_key(self, tmp_path: Path) -> None:
        """Places the entry inside the repos block when other keys follow it."""

        head = "default_stages: [pre-commit]\nrepos:\n  - repo: https://example.com/a\n    rev: v1\n"
        tail = "\nci:\n  autofix_prs: false\n"
        assert install(tmp_path, head + tail) == head + entry("  ") + tail

    def test_fills_empty_repos_block(self, tmp_path: Path) -> None:
        """Uses two spaces of indentation when the list has no items yet."""

        assert install(tmp_path, "repos:\n") == "repos:\n" + entry("  ")

    def test_adds_missing_final_newline(self, tmp_path: Path) -> None:
        """Ends the previous last line before appending when the file lacks a final newline."""

        text = "repos:\n  - repo: https://example.com/a\n    rev: v1"
        assert install(tmp_path, text) == text + "\n" + entry("  ")

    def test_keeps_comments_after_block(self, tmp_path: Path) -> None:
        """Leaves trailing comments below the inserted entry."""

        text = "repos:\n  - repo: https://example.com/a\n# trailing comment\n"
        assert install(tmp_path, text) == "repos:\n  - repo: https://example.com/a\n" + entry("  ") + "# trailing comment\n"

    def test_keeps_crlf_line_endings(self, tmp_path: Path) -> None:
        """Writes the entry with CRLF line breaks when the file uses CRLF."""

        text = "repos:\r\n  - repo: https://example.com/a\r\n"
        assert install(tmp_path, text) == text + entry("  ").replace("\n", "\r\n")

    def test_quotes_target_with_spaces(self, tmp_path: Path) -> None:
        """Writes a target containing spaces as a double-quoted string."""

        assert install(tmp_path, "repos:\n", "docs/my file.md") == "repos:\n" + entry("  ", '"docs/my file.md"')

    def test_skips_existing_entry(self, tmp_path: Path) -> None:
        """Returns False and leaves the file untouched when fsg is already configured."""

        text = "repos:\n  - repo: https://github.com/KarnesTH/fsg\n    rev: v0.1.0\n"
        config = tmp_path / ".pre-commit-config.yaml"
        config.write_text(text, encoding="utf-8")
        assert PreCommitHook(tmp_path, "README.md").install() is False
        assert config.read_text(encoding="utf-8") == text

    @pytest.mark.parametrize("text", ["repos: []\n", "default_stages: [pre-commit]\n", "  repos:\n"])
    def test_rejects_config_without_block_repos(self, tmp_path: Path, text: str) -> None:
        """Raises HookError with a hint and leaves the file untouched when no top-level block repos key exists."""

        config = tmp_path / ".pre-commit-config.yaml"
        config.write_text(text, encoding="utf-8")
        with pytest.raises(HookError, match="repos") as error:
            PreCommitHook(tmp_path, "README.md").install()
        assert "manually" in error.value.hint
        assert config.read_text(encoding="utf-8") == text
    @pytest.mark.parametrize(
        "line",
        [
            "  - repo: https://github.com/KarnesTH/fsg",
            "-   repo: 'https://github.com/karnesth/fsg.git'  # tree",
            '  - repo: "https://github.com/KarnesTH/fsg/"',
        ],
    )
    def test_detects_existing_repo_line(self, tmp_path: Path, line: str) -> None:
        """Recognizes the fsg repository in quoted, .git and commented forms."""

        config = tmp_path / ".pre-commit-config.yaml"
        config.write_text(f"repos:\n{line}\n", encoding="utf-8")
        assert PreCommitHook(tmp_path, "README.md").install() is False

    def test_ignores_similar_repositories_and_comments(self, tmp_path: Path) -> None:
        """Adds the entry when only a comment or another repository mentions the fsg name."""

        text = "# see KarnesTH/fsg\nrepos:\n  - repo: https://github.com/KarnesTH/fsg-tools\n"
        assert "id: fsg" in install(tmp_path, text)

    def test_rejects_unknown_version(self, tmp_path: Path, monkeypatch) -> None:
        """Raises HookError instead of writing an invalid rev when the installed version is unknown."""

        monkeypatch.setattr("fsg.__version__", "unknown")
        config = tmp_path / ".pre-commit-config.yaml"
        config.write_text("repos:\n", encoding="utf-8")
        with pytest.raises(HookError, match="version"):
            PreCommitHook(tmp_path, "README.md").install()
        assert config.read_text(encoding="utf-8") == "repos:\n"