from pathlib import Path

from fsg.constants import ASCII_GLYPHS
from fsg.trees import GitProjectTree, PlainProjectTree, ProjectTree
from tests.conftest import create_files, init_repository, requires_git


class TestForPath:
    """Covers the selection of the collecting implementation."""

    @requires_git
    def test_returns_git_tree_inside_repository(self, tmp_path: Path) -> None:
        """Selects GitProjectTree when the directory is a git working tree."""

        init_repository(tmp_path)
        assert isinstance(ProjectTree.for_path(tmp_path), GitProjectTree)

    def test_returns_plain_tree_without_repository(self, tmp_path: Path) -> None:
        """Selects PlainProjectTree when the directory is not inside a repository."""

        assert isinstance(ProjectTree.for_path(tmp_path), PlainProjectTree)

    @requires_git
    def test_returns_git_tree_in_subdirectory_of_repository(self, tmp_path: Path) -> None:
        """Selects GitProjectTree for a subdirectory of a repository."""

        init_repository(tmp_path)
        subdirectory = tmp_path / "gui"
        subdirectory.mkdir()
        assert isinstance(ProjectTree.for_path(subdirectory), GitProjectTree)

    def test_passes_ascii_option(self, tmp_path: Path) -> None:
        """Hands the ASCII option over to the selected implementation."""

        assert ProjectTree.for_path(tmp_path, use_ascii=True).glyphs == ASCII_GLYPHS


class TestCollect:
    """Covers the interface the collecting implementations fill in."""

    def test_raises_without_implementation(self, tmp_path: Path) -> None:
        """Rejects collecting on the base class itself."""

        try:
            ProjectTree(tmp_path).collect()
        except NotImplementedError:
            return
        raise AssertionError("collect did not raise NotImplementedError")


class TestRender:
    """Covers the rendered output of the tree."""

    def test_wraps_output_in_code_fence(self, tmp_path: Path) -> None:
        """Surrounds the tree with a plaintext Markdown fence."""

        create_files(tmp_path, ["__main__.py"])
        output = PlainProjectTree(tmp_path).render()
        assert output.startswith("```plaintext\n")
        assert output.endswith("\n```")

    def test_starts_with_root_directory_name(self, tmp_path: Path) -> None:
        """Renders the resolved directory name followed by a slash as the first line."""

        create_files(tmp_path, ["__main__.py"])
        assert PlainProjectTree(tmp_path).render().splitlines()[1] == f"{tmp_path.name}/"

    def test_renders_directories_before_files(self, tmp_path: Path) -> None:
        """Places directories above files on the same level."""

        create_files(tmp_path, ["README.md", "src/__main__.py"])
        lines = PlainProjectTree(tmp_path).render().splitlines()
        assert lines[2:] == [
            "├── src/",
            "│   └── __main__.py",
            "└── README.md",
            "```",
        ]

    def test_sorts_entries_case_insensitively(self, tmp_path: Path) -> None:
        """Orders entries of the same kind by lowercased name."""

        create_files(tmp_path, ["beta.py", "Alpha.py", "gamma.py"])
        lines = PlainProjectTree(tmp_path).render().splitlines()
        assert lines[2:5] == ["├── Alpha.py", "├── beta.py", "└── gamma.py"]

    def test_marks_directories_with_trailing_slash(self, tmp_path: Path) -> None:
        """Appends a slash to directory names only."""

        create_files(tmp_path, ["src/__main__.py"])
        output = PlainProjectTree(tmp_path).render()
        assert "└── src/" in output
        assert "└── __main__.py" in output

    def test_indents_nested_levels(self, tmp_path: Path) -> None:
        """Carries the pipe prefix into the children of a directory that is not last."""

        create_files(tmp_path, ["src/gui/window.py", "README.md"])
        lines = PlainProjectTree(tmp_path).render().splitlines()
        assert lines[2:6] == [
            "├── src/",
            "│   └── gui/",
            "│       └── window.py",
            "└── README.md",
        ]

    def test_renders_empty_project(self, tmp_path: Path) -> None:
        """Renders only the root line when there is nothing to list."""

        assert PlainProjectTree(tmp_path).render() == f"```plaintext\n{tmp_path.name}/\n```"

    def test_resolves_relative_paths(self, tmp_path: Path, monkeypatch) -> None:
        """Uses the resolved directory name when the tree is created from a relative path."""

        create_files(tmp_path, ["__main__.py"])
        monkeypatch.chdir(tmp_path)
        assert PlainProjectTree(Path(".")).render().splitlines()[1] == f"{tmp_path.name}/"
    def test_renders_ascii_connectors(self, tmp_path: Path) -> None:
        """Draws branches, last entries and pipes with ASCII characters when use_ascii is set."""

        create_files(tmp_path, ["src/gui/window.py", "README.md"])
        lines = PlainProjectTree(tmp_path, use_ascii=True).render().splitlines()
        assert lines[2:6] == [
            "|-- src/",
            "|   `-- gui/",
            "|       `-- window.py",
            "`-- README.md",
        ]