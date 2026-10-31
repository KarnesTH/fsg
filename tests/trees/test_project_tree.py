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

    def test_passes_render_options(self, tmp_path: Path) -> None:
        """Hands depth, dirs_only, exclude and fence over to the selected implementation."""

        tree = ProjectTree.for_path(tmp_path, depth=2, dirs_only=True, exclude=["*.pyc"], fence=False)
        assert (tree.depth, tree.dirs_only, tree.exclude, tree.fence) == (2, True, ("*.pyc",), False)


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


class TestDepth:
    """Covers limiting the rendered levels."""

    def test_renders_only_top_level(self, tmp_path: Path) -> None:
        """Renders the entries directly below the root and keeps the slash on directories."""

        create_files(tmp_path, ["src/gui/window.py", "README.md"])
        lines = PlainProjectTree(tmp_path, depth=1).render().splitlines()
        assert lines[2:-1] == ["├── src/", "└── README.md"]

    def test_renders_given_number_of_levels(self, tmp_path: Path) -> None:
        """Stops descending once the given level is reached."""

        create_files(tmp_path, ["src/gui/window.py", "src/main.py"])
        output = PlainProjectTree(tmp_path, depth=2).render()
        assert "gui/" in output
        assert "main.py" in output
        assert "window.py" not in output

    def test_renders_all_levels_without_limit(self, tmp_path: Path) -> None:
        """Renders every level when no depth is given."""

        create_files(tmp_path, ["a/b/c/d/e.py"])
        assert "e.py" in PlainProjectTree(tmp_path).render()


class TestDirsOnly:
    """Covers rendering directories only."""

    def test_leaves_out_files(self, tmp_path: Path) -> None:
        """Renders the directory structure without any file."""

        create_files(tmp_path, ["README.md", "src/main.py", "src/gui/window.py"])
        lines = PlainProjectTree(tmp_path, dirs_only=True).render().splitlines()
        assert lines[2:-1] == ["└── src/", "    └── gui/"]

    def test_marks_last_directory_after_trailing_files(self, tmp_path: Path) -> None:
        """Uses the last connector for the final directory even when files follow it."""

        create_files(tmp_path, ["docs/a.md", "src/main.py", "z.txt"])
        lines = PlainProjectTree(tmp_path, dirs_only=True).render().splitlines()
        assert lines[2:-1] == ["├── docs/", "└── src/"]


class TestExclude:
    """Covers leaving out entries by glob pattern."""

    def test_excludes_by_name(self, tmp_path: Path) -> None:
        """Leaves out every entry whose name matches the pattern."""

        create_files(tmp_path, ["main.py", "notes.txt", "docs/todo.txt"])
        output = PlainProjectTree(tmp_path, exclude=["*.txt"]).render()
        assert "main.py" in output
        assert ".txt" not in output
        assert "docs" not in output

    def test_excludes_directory_with_content(self, tmp_path: Path) -> None:
        """Leaves out a directory and everything below it when its name matches."""

        create_files(tmp_path, ["main.py", "tests/test_main.py"])
        output = PlainProjectTree(tmp_path, exclude=["tests"]).render()
        assert "tests" not in output
        assert "test_main.py" not in output

    def test_excludes_by_relative_path(self, tmp_path: Path) -> None:
        """Matches the pattern against the relative path so nested entries can be targeted."""

        create_files(tmp_path, ["docs/api/index.md", "docs/guide.md", "api/client.py"])
        output = PlainProjectTree(tmp_path, exclude=["docs/api"]).render()
        assert "index.md" not in output
        assert "guide.md" in output
        assert "client.py" in output

    def test_matches_case_sensitively(self, tmp_path: Path) -> None:
        """Keeps entries whose name differs from the pattern only in case."""

        create_files(tmp_path, ["README.md"])
        assert "README.md" in PlainProjectTree(tmp_path, exclude=["readme.md"]).render()

    def test_combines_multiple_patterns(self, tmp_path: Path) -> None:
        """Leaves out entries matching any of the given patterns."""

        create_files(tmp_path, ["main.py", "a.log", "b.tmp"])
        output = PlainProjectTree(tmp_path, exclude=["*.log", "*.tmp"]).render()
        assert "main.py" in output
        assert "a.log" not in output
        assert "b.tmp" not in output


class TestFence:
    """Covers disabling the code fence."""

    def test_renders_without_fence(self, tmp_path: Path) -> None:
        """Returns the bare tree when fence is disabled."""

        create_files(tmp_path, ["main.py"])
        assert PlainProjectTree(tmp_path, fence=False).render() == f"{tmp_path.name}/\n└── main.py"