from pathlib import Path

import pytest

from fsg.glyphs import Glyphs
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

        assert ProjectTree.for_path(tmp_path, glyphs=Glyphs.from_style("ascii")).glyphs == Glyphs.from_style("ascii")

    def test_passes_render_options(self, tmp_path: Path) -> None:
        """Hands depth, dirs_only, exclude and fence over to the selected implementation."""

        tree = ProjectTree.for_path(tmp_path, depth=2, dirs_only=True, exclude=["*.pyc"], include=["*.py"], fence=False)
        assert (tree.depth, tree.dirs_only, tree.exclude, tree.include, tree.fence) == (
            2, True, ("*.pyc",), ("*.py",), False,
        )


class TestCollect:
    """Covers the interface the collecting implementations fill in."""

    def test_cannot_instantiate_base_class(self, tmp_path: Path) -> None:
        """Rejects creating the abstract base class without a collect implementation."""

        with pytest.raises(TypeError, match="abstract"):
            ProjectTree(tmp_path)


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
        """Draws branches, last entries and pipes with the ASCII glyphs."""

        create_files(tmp_path, ["src/gui/window.py", "README.md"])
        lines = PlainProjectTree(tmp_path, glyphs=Glyphs.from_style("ascii")).render().splitlines()
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


class TestInclude:
    """Covers keeping only entries that match an include pattern."""

    def test_keeps_matching_files(self, tmp_path: Path) -> None:
        """Renders only files whose name matches and the directories leading to them."""

        create_files(tmp_path, ["main.py", "README.md", "src/app.py", "docs/guide.md"])
        lines = PlainProjectTree(tmp_path, include=["*.py"], fence=False).render().splitlines()
        assert lines[1:] == ["├── src/", "│   └── app.py", "└── main.py"]

    def test_includes_directory_by_name(self, tmp_path: Path) -> None:
        """Keeps everything below a directory whose name matches."""

        create_files(tmp_path, ["src/app.py", "src/data.json", "docs/guide.md"])
        output = PlainProjectTree(tmp_path, include=["src"]).render()
        assert "app.py" in output
        assert "data.json" in output
        assert "guide.md" not in output

    def test_includes_by_relative_path(self, tmp_path: Path) -> None:
        """Matches the pattern against the relative path."""

        create_files(tmp_path, ["docs/api/index.md", "docs/guide.md"])
        output = PlainProjectTree(tmp_path, include=["docs/api/*"]).render()
        assert "index.md" in output
        assert "guide.md" not in output

    def test_exclude_wins_over_include(self, tmp_path: Path) -> None:
        """Leaves out included files that also match an exclude pattern."""

        create_files(tmp_path, ["src/app.py", "tests/test_app.py"])
        output = PlainProjectTree(tmp_path, include=["*.py"], exclude=["tests"]).render()
        assert "app.py" in output
        assert "test_app.py" not in output

    def test_combines_multiple_patterns(self, tmp_path: Path) -> None:
        """Keeps files matching any of the patterns."""

        create_files(tmp_path, ["a.py", "b.md", "c.txt"])
        output = PlainProjectTree(tmp_path, include=["*.py", "*.md"]).render()
        assert "a.py" in output
        assert "b.md" in output
        assert "c.txt" not in output

    def test_matches_directories_with_dirs_only(self, tmp_path: Path) -> None:
        """Matches the include patterns against directory names when only directories are rendered."""

        create_files(tmp_path, ["src/core/a.py", "src/gui/b.py", "docs/c.md"])
        lines = PlainProjectTree(tmp_path, include=["src"], dirs_only=True, fence=False).render().splitlines()
        assert lines[1:] == ["└── src/", "    ├── core/", "    └── gui/"]

    def test_renders_empty_tree_without_matches(self, tmp_path: Path) -> None:
        """Renders only the root when no file matches."""

        create_files(tmp_path, ["a.py"])
        assert PlainProjectTree(tmp_path, include=["*.rs"], fence=False).render() == f"{tmp_path.name}/"


class TestFence:
    """Covers disabling the code fence."""

    def test_renders_without_fence(self, tmp_path: Path) -> None:
        """Returns the bare tree when fence is disabled."""

        create_files(tmp_path, ["main.py"])
        assert PlainProjectTree(tmp_path, fence=False).render() == f"{tmp_path.name}/\n└── main.py"

class TestSummary:
    """Covers the line counting directories and files."""

    def test_counts_rendered_entries(self, tmp_path: Path) -> None:
        """Counts the rendered directories and files below the root."""

        create_files(tmp_path, ["a.py", "src/b.py", "src/gui/c.py"])
        lines = PlainProjectTree(tmp_path, summary=True, fence=False).render().splitlines()
        assert lines[-2:] == ["", "2 directories, 3 files"]

    def test_uses_singular_nouns(self, tmp_path: Path) -> None:
        """Writes directory and file for counts of one."""

        create_files(tmp_path, ["src/a.py"])
        assert PlainProjectTree(tmp_path, summary=True, fence=False).render().endswith("1 directory, 1 file")

    def test_counts_only_shown_levels(self, tmp_path: Path) -> None:
        """Leaves out entries below the depth limit."""

        create_files(tmp_path, ["src/gui/c.py", "a.py"])
        assert PlainProjectTree(tmp_path, summary=True, depth=1, fence=False).render().endswith("1 directory, 1 file")

    def test_stays_inside_fence(self, tmp_path: Path) -> None:
        """Places the summary before the closing fence."""

        create_files(tmp_path, ["a.py"])
        assert PlainProjectTree(tmp_path, summary=True).render().endswith("0 directories, 1 file\n```")


class TestComments:
    """Covers attaching comments to rendered lines."""

    def test_aligns_comments(self, tmp_path: Path) -> None:
        """Appends the comments two columns after the longest commented line."""

        create_files(tmp_path, ["src/cli.py", "README.md"])
        output = PlainProjectTree(tmp_path, fence=False).render({"": "root", "src/cli.py": "entry", "README.md": "docs"})
        column = max(len(f"{tmp_path.name}/"), len("│   └── cli.py"), len("└── README.md")) + 2
        assert output.splitlines() == [
            f"{tmp_path.name}/".ljust(column) + "# root",
            "├── src/",
            "│   └── cli.py".ljust(column) + "# entry",
            "└── README.md".ljust(column) + "# docs",
        ]

    def test_ignores_comments_of_missing_paths(self, tmp_path: Path) -> None:
        """Drops comments whose path is no longer rendered."""

        create_files(tmp_path, ["a.py"])
        assert "#" not in PlainProjectTree(tmp_path, fence=False).render({"gone.py": "old"})

    def test_aligns_by_display_width(self, tmp_path: Path) -> None:
        """Measures lines in terminal columns, so box drawing characters count once."""

        create_files(tmp_path, ["ab.py", "c.py"])
        lines = PlainProjectTree(tmp_path, fence=False).render({"ab.py": "x", "c.py": "y"}).splitlines()
        assert lines[1].index("#") == lines[2].index("#")