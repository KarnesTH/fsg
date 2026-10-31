import io
from pathlib import Path

import pytest

import fsg
from fsg.cli import main, parse_args
from fsg.errors import ClipboardError, GitError
from fsg.marked_file import END_MARKER, START_MARKER
from tests.conftest import create_files, init_repository, requires_git


class TestParseArgs:
    """Covers the argument parsing."""

    def test_reads_path_argument(self) -> None:
        """Returns the given path as a Path object."""

        assert parse_args(["src"]).path == Path("src")

    def test_leaves_path_unset(self) -> None:
        """Returns None when no path is given."""

        assert parse_args([]).path is None

    def test_rejects_further_arguments(self) -> None:
        """Exits when more than one path is given."""

        with pytest.raises(SystemExit):
            parse_args(["src", "tests"])

    def test_ascii_defaults_to_none(self) -> None:
        """Returns None for use_ascii when the option is not given."""

        assert parse_args([]).use_ascii is None

    def test_reads_ascii_option(self) -> None:
        """Returns True for use_ascii when --ascii is given."""

        assert parse_args(["--ascii"]).use_ascii is True

    def test_render_options_default(self) -> None:
        """Returns None for every option that can come from the config and no exclusions when no option is given."""

        args = parse_args([])
        assert (args.depth, args.dirs_only, args.exclude, args.include, args.fence) == (None, None, [], [], None)

    def test_reads_render_options(self) -> None:
        """Reads depth, dirs-only, repeated excludes and no-fence."""

        args = parse_args(["-d", "2", "--dirs-only", "-e", "*.log", "--exclude", "tests", "-i", "*.py", "--include", "*.md", "--no-fence"])
        assert (args.depth, args.dirs_only, args.exclude, args.include, args.fence) == (
            2, True, ["*.log", "tests"], ["*.py", "*.md"], False,
        )

    def test_reads_negated_options(self) -> None:
        """Returns False for options switched off with their --no- form."""

        args = parse_args(["--no-dirs-only", "--no-ascii", "--fence"])
        assert (args.dirs_only, args.use_ascii, args.fence) == (False, False, True)

    def test_rejects_setup_hook_together_with_update(self) -> None:
        """Exits when --setup-hook and --update are given at the same time."""

        with pytest.raises(SystemExit):
            parse_args(["--setup-hook", "README.md", "--update", "README.md"])

    @pytest.mark.parametrize("depth", ["0", "-1"])
    def test_rejects_depth_below_one(self, depth: str, capsys) -> None:
        """Exits with status 2 when the depth is smaller than 1."""

        with pytest.raises(SystemExit) as exit_info:
            parse_args(["--depth", depth])
        assert exit_info.value.code == 2
        assert "--depth must be at least 1" in capsys.readouterr().err

    def test_rejects_non_numeric_depth(self) -> None:
        """Exits when the depth is not an integer."""

        with pytest.raises(SystemExit):
            parse_args(["--depth", "two"])

    def test_rejects_unknown_options(self) -> None:
        """Exits when an unknown option is given."""

        with pytest.raises(SystemExit):
            parse_args(["--unknown"])


class TestMain:
    """Covers the command line entry point."""

    def test_prints_tree_for_given_path(self, tmp_path: Path, capsys) -> None:
        """Writes the tree of the path passed as the first argument to stdout."""

        create_files(tmp_path, ["main.py"])
        assert main([str(tmp_path)]) == 0
        assert "main.py" in capsys.readouterr().out

    def test_uses_current_directory_without_arguments(self, tmp_path: Path, capsys, monkeypatch) -> None:
        """Renders the current working directory when no argument is given."""

        create_files(tmp_path, ["main.py"])
        monkeypatch.chdir(tmp_path)
        assert main([]) == 0
        output = capsys.readouterr().out
        assert f"{tmp_path.name}/" in output
        assert "main.py" in output

    def test_reads_command_line_arguments(self, tmp_path: Path, capsys, monkeypatch) -> None:
        """Falls back to sys.argv when no argument list is passed."""

        create_files(tmp_path, ["main.py"])
        monkeypatch.setattr("sys.argv", ["fsg", str(tmp_path)])
        assert main() == 0
        assert "main.py" in capsys.readouterr().out

    def test_reports_missing_directory(self, tmp_path: Path, capsys) -> None:
        """Writes an error to stderr and returns 1 when the path does not exist."""

        missing = tmp_path / "missing"
        assert main([str(missing)]) == 2
        assert capsys.readouterr().err == (
            f"✖ {missing}: not a directory\n  hint: pass an existing directory or set path in the config or marker\n"
        )

    def test_reports_file_instead_of_directory(self, tmp_path: Path, capsys) -> None:
        """Writes an error to stderr and returns 1 when the path is a file."""

        create_files(tmp_path, ["main.py"])
        assert main([str(tmp_path / "main.py")]) == 2
        assert capsys.readouterr().err.startswith(f"✖ {tmp_path / 'main.py'}: not a directory\n")

    def test_prints_help(self, capsys) -> None:
        """Exits after writing the usage text to stdout."""

        with pytest.raises(SystemExit) as exit_info:
            main(["--help"])
        assert exit_info.value.code == 0
        assert "usage: fsg" in capsys.readouterr().out

    def test_prints_help_with_short_option(self, capsys) -> None:
        """Exits after writing the usage text to stdout when -h is given."""

        with pytest.raises(SystemExit) as exit_info:
            main(["-h"])
        assert exit_info.value.code == 0
        assert "usage: fsg" in capsys.readouterr().out

    @pytest.mark.parametrize("option", ["--version", "-V"])
    def test_prints_version(self, option: str, capsys) -> None:
        """Exits after writing the program name and the installed package version to stdout."""

        with pytest.raises(SystemExit) as exit_info:
            main([option])
        assert exit_info.value.code == 0
        assert capsys.readouterr().out.strip() == f"fsg {fsg.__version__}"
    def test_prints_ascii_tree(self, tmp_path: Path, capsys) -> None:
        """Writes the tree with ASCII connectors when --ascii is given."""

        create_files(tmp_path, ["main.py"])
        assert main(["--ascii", str(tmp_path)]) == 0
        output = capsys.readouterr().out
        assert "`-- main.py" in output
        assert "└──" not in output

    def test_writes_utf8_to_non_utf8_stdout(self, tmp_path: Path, monkeypatch) -> None:
        """Switches a stdout with a legacy encoding to UTF-8 before writing the tree."""

        create_files(tmp_path, ["main.py"])
        buffer = io.BytesIO()
        stdout = io.TextIOWrapper(buffer, encoding="cp1252")
        monkeypatch.setattr("sys.stdout", stdout)
        assert main([str(tmp_path)]) == 0
        stdout.flush()
        assert "└── main.py" in buffer.getvalue().decode("utf-8")

    def test_applies_render_options(self, tmp_path: Path, capsys) -> None:
        """Passes the parsed options on to the rendered tree."""

        create_files(tmp_path, ["main.py", "src/app.py", "src/gui/window.py", "debug.log"])
        assert main(["--depth", "2", "--exclude", "*.log", "--no-fence", str(tmp_path)]) == 0
        output = capsys.readouterr().out
        assert not output.startswith("```")
        assert "app.py" in output
        assert "window.py" not in output
        assert "debug.log" not in output

    def test_applies_dirs_only(self, tmp_path: Path, capsys) -> None:
        """Renders directories only when --dirs-only is given."""

        create_files(tmp_path, ["main.py", "src/app.py"])
        assert main(["--dirs-only", str(tmp_path)]) == 0
        output = capsys.readouterr().out
        assert "src/" in output
        assert "main.py" not in output


class TestSync:
    """Covers updating and checking the marked section of a file."""

    def test_rejects_update_together_with_check(self, tmp_path: Path) -> None:
        """Exits when --update and --check are given at the same time."""

        with pytest.raises(SystemExit):
            parse_args(["--update", "README.md", "--check", "README.md"])

    def test_update_writes_tree_into_section(self, tmp_path: Path, capsys) -> None:
        """Writes the rendered tree between the markers and reports the change on stdout."""

        create_files(tmp_path, ["main.py"])
        readme = tmp_path / "README.md"
        readme.write_text(f"# Title\n{START_MARKER}\n{END_MARKER}\n", encoding="utf-8")
        assert main(["--update", str(readme), str(tmp_path)]) == 0
        text = readme.read_text(encoding="utf-8")
        assert "── main.py" in text
        assert text.startswith(f"# Title\n{START_MARKER}\n```plaintext\n")
        assert capsys.readouterr().out == f"✔ {readme}: tree updated\n"

    def test_update_reports_current_tree(self, tmp_path: Path, capsys) -> None:
        """Reports that nothing changed when the section is already current."""

        create_files(tmp_path, ["main.py"])
        readme = tmp_path / "README.md"
        readme.write_text(f"{START_MARKER}\n{END_MARKER}\n", encoding="utf-8")
        main(["--update", str(readme), str(tmp_path)])
        capsys.readouterr()
        assert main(["--update", str(readme), str(tmp_path)]) == 0
        assert capsys.readouterr().out == f"• {readme}: tree already up to date\n"

    def test_check_reports_current_tree(self, tmp_path: Path, capsys) -> None:
        """Reports on stdout that the tree is up to date."""

        create_files(tmp_path, ["main.py"])
        readme = tmp_path / "README.md"
        readme.write_text(f"{START_MARKER}\n{END_MARKER}\n", encoding="utf-8")
        main(["--update", str(readme), str(tmp_path)])
        capsys.readouterr()
        assert main(["--check", str(readme), str(tmp_path)]) == 0
        assert capsys.readouterr().out == f"✔ {readme}: tree is up to date\n"

    def test_check_passes_after_update(self, tmp_path: Path) -> None:
        """Returns 0 when the section matches the tree rendered with the same options."""

        create_files(tmp_path, ["main.py", "src/app.py"])
        readme = tmp_path / "README.md"
        readme.write_text(f"{START_MARKER}\n{END_MARKER}\n", encoding="utf-8")
        main(["-u", str(readme), "--depth", "1", str(tmp_path)])
        assert main(["-c", str(readme), "--depth", "1", str(tmp_path)]) == 0

    def test_check_fails_on_outdated_section(self, tmp_path: Path, capsys) -> None:
        """Returns 1 and reports the file on stderr when a new file is missing from the section."""

        create_files(tmp_path, ["main.py"])
        readme = tmp_path / "README.md"
        readme.write_text(f"{START_MARKER}\n{END_MARKER}\n", encoding="utf-8")
        main(["--update", str(readme), str(tmp_path)])
        create_files(tmp_path, ["new.py"])
        capsys.readouterr()
        assert main(["--check", str(readme), str(tmp_path)]) == 1
        assert capsys.readouterr().err == f"✖ {readme}: tree is out of date\n  hint: run fsg --update {readme}\n"

    def test_check_does_not_modify_file(self, tmp_path: Path) -> None:
        """Leaves the file unchanged when the section is outdated."""

        create_files(tmp_path, ["main.py"])
        readme = tmp_path / "README.md"
        readme.write_text(f"{START_MARKER}\nold\n{END_MARKER}\n", encoding="utf-8")
        main(["--check", str(readme), str(tmp_path)])
        assert readme.read_text(encoding="utf-8") == f"{START_MARKER}\nold\n{END_MARKER}\n"

    @pytest.mark.parametrize("option", ["--update", "--check"])
    def test_reports_missing_markers(self, option: str, tmp_path: Path, capsys) -> None:
        """Returns 2 and reports the missing markers on stderr."""

        readme = tmp_path / "README.md"
        readme.write_text("# Title\n", encoding="utf-8")
        assert main([option, str(readme), str(tmp_path)]) == 2
        assert capsys.readouterr().err == (
            f"✖ {readme}: missing {START_MARKER} marker\n"
            f"  hint: add {START_MARKER} and {END_MARKER} on their own lines outside a code block\n"
        )

    @pytest.mark.parametrize("option", ["--update", "--check"])
    def test_reports_missing_file(self, option: str, tmp_path: Path, capsys) -> None:
        """Returns 2 and reports the error on stderr when the file does not exist."""

        missing = tmp_path / "MISSING.md"
        assert main([option, str(missing), str(tmp_path)]) == 2
        assert capsys.readouterr().err == f"✖ {missing}: file not found\n"

    def test_reports_non_utf8_file(self, tmp_path: Path, capsys) -> None:
        """Returns 2 and reports a file that is not UTF-8 encoded."""

        readme = tmp_path / "README.md"
        readme.write_bytes(b"\xff\xfe\x00")
        assert main(["--check", str(readme), str(tmp_path)]) == 2
        assert capsys.readouterr().err == f"✖ {readme}: not a UTF-8 text file\n"


class TestConfig:
    """Covers reading the path and options from a config file in update and check mode."""

    @staticmethod
    def readme(root: Path) -> Path:
        """Creates a README.md with empty markers below the root and returns its path.

        Args:
            root: Directory the file is created in.
        """

        readme = root / "README.md"
        readme.write_text(f"{START_MARKER}\n{END_MARKER}\n", encoding="utf-8")
        return readme

    def test_applies_config_on_update(self, tmp_path: Path) -> None:
        """Renders the tree written by --update with the options from .fsg.toml."""

        create_files(tmp_path, ["main.py", "debug.log", "src/app.py"])
        (tmp_path / ".fsg.toml").write_text('exclude = ["*.log"]\nfence = false\ndepth = 1\n', encoding="utf-8")
        readme = self.readme(tmp_path)
        assert main(["--update", str(readme), str(tmp_path)]) == 0
        text = readme.read_text(encoding="utf-8")
        assert "```" not in text
        assert "debug.log" not in text
        assert "app.py" not in text

    def test_reads_path_from_config(self, tmp_path: Path) -> None:
        """Renders the configured path, resolved against the config file, when no path is given."""

        create_files(tmp_path, ["main.py", "src/app.py"])
        (tmp_path / ".fsg.toml").write_text('path = "src"\n', encoding="utf-8")
        readme = self.readme(tmp_path)
        assert main(["--update", str(readme)]) == 0
        text = readme.read_text(encoding="utf-8")
        assert "src/\n└── app.py" in text
        assert "main.py" not in text

    def test_checks_with_config_path(self, tmp_path: Path, monkeypatch) -> None:
        """Finds the tree of the configured path up to date after an update from another directory."""

        create_files(tmp_path, ["src/app.py"])
        (tmp_path / "pyproject.toml").write_text('[tool.fsg]\npath = "src"\ndepth = 2\n', encoding="utf-8")
        readme = self.readme(tmp_path)
        main(["--update", str(readme)])
        monkeypatch.chdir(tmp_path / "src")
        assert main(["--check", str(readme)]) == 0

    def test_argument_path_overrides_config_path(self, tmp_path: Path) -> None:
        """Renders the path given on the command line instead of the configured one."""

        create_files(tmp_path, ["src/app.py", "docs/guide.md"])
        (tmp_path / ".fsg.toml").write_text('path = "src"\n', encoding="utf-8")
        readme = self.readme(tmp_path)
        main(["--update", str(readme), str(tmp_path / "docs")])
        text = readme.read_text(encoding="utf-8")
        assert "guide.md" in text
        assert "app.py" not in text

    def test_arguments_override_config(self, tmp_path: Path) -> None:
        """Prefers options given on the command line over the config file."""

        create_files(tmp_path, ["main.py"])
        (tmp_path / ".fsg.toml").write_text("fence = false\n", encoding="utf-8")
        readme = self.readme(tmp_path)
        main(["--update", str(readme), "--fence", str(tmp_path)])
        assert "```plaintext" in readme.read_text(encoding="utf-8")

    def test_ignores_config_without_mode(self, tmp_path: Path, capsys, monkeypatch) -> None:
        """Renders the current directory with the defaults when neither --update nor --check is given."""

        create_files(tmp_path, ["main.py", "src/app.py"])
        (tmp_path / ".fsg.toml").write_text('path = "src"\nfence = false\n', encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        assert main([]) == 0
        output = capsys.readouterr().out
        assert output.startswith(f"```plaintext\n{tmp_path.name}/")
        assert "main.py" in output

    def test_reports_invalid_config(self, tmp_path: Path, capsys) -> None:
        """Returns 2 and reports the problem when the config holds an invalid value."""

        (tmp_path / ".fsg.toml").write_text("depth = 0\n", encoding="utf-8")
        assert main(["--check", str(self.readme(tmp_path)), str(tmp_path)]) == 2
        assert capsys.readouterr().err.startswith("✖ ")

    def test_reports_missing_config_path(self, tmp_path: Path, capsys) -> None:
        """Returns 1 and names the configured path when it is not a directory."""

        (tmp_path / ".fsg.toml").write_text('path = "gone"\n', encoding="utf-8")
        assert main(["--check", str(self.readme(tmp_path))]) == 2
        assert capsys.readouterr().err.startswith(f"✖ {(tmp_path / 'gone').resolve()}: not a directory\n")


def write_markers(path: Path) -> Path:
    """Creates the file with an empty marker block, including missing parent directories, and returns its path.

    Args:
        path: File to create.
    """

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{START_MARKER}\n{END_MARKER}\n", encoding="utf-8")
    return path


@requires_git
class TestSetupHook:
    """Covers adding the update step to the commit hooks."""

    def test_installs_git_hook(self, tmp_path: Path, capsys, monkeypatch) -> None:
        """Creates the native pre-commit hook and reports its location."""

        init_repository(tmp_path)
        write_markers(tmp_path / "README.md")
        monkeypatch.chdir(tmp_path)
        assert main(["--setup-hook", "README.md"]) == 0
        assert "fsg --update README.md" in (tmp_path / ".git" / "hooks" / "pre-commit").read_text(encoding="utf-8")
        assert capsys.readouterr().out == "✔ .git/hooks/pre-commit: fsg hook added\n"

    def test_extends_pre_commit_config(self, tmp_path: Path, capsys, monkeypatch) -> None:
        """Adds the entry to an existing .pre-commit-config.yaml and reminds to install pre-commit."""

        init_repository(tmp_path)
        write_markers(tmp_path / "README.md")
        (tmp_path / ".pre-commit-config.yaml").write_text("repos:\n", encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        assert main(["--setup-hook", "README.md"]) == 0
        assert "id: fsg" in (tmp_path / ".pre-commit-config.yaml").read_text(encoding="utf-8")
        assert "pre-commit install" in capsys.readouterr().out

    def test_reports_existing_hook(self, tmp_path: Path, capsys, monkeypatch) -> None:
        """Reports that the hook is already present on a second run."""

        init_repository(tmp_path)
        write_markers(tmp_path / "README.md")
        monkeypatch.chdir(tmp_path)
        main(["--setup-hook", "README.md"])
        capsys.readouterr()
        assert main(["--setup-hook", "README.md"]) == 0
        assert capsys.readouterr().out == "• .git/hooks/pre-commit: fsg hook already present\n"

    def test_uses_path_relative_to_repository(self, tmp_path: Path, monkeypatch) -> None:
        """Writes the target relative to the repository root when run from a subdirectory."""

        init_repository(tmp_path)
        write_markers(tmp_path / "docs" / "index.md")
        monkeypatch.chdir(tmp_path / "docs")
        assert main(["--setup-hook", "index.md"]) == 0
        assert "fsg --update docs/index.md" in (tmp_path / ".git" / "hooks" / "pre-commit").read_text(encoding="utf-8")

    def test_rejects_directory_outside_repository(self, tmp_path: Path, capsys, monkeypatch) -> None:
        """Returns 2 when the current directory is not inside a git repository."""

        monkeypatch.chdir(tmp_path)
        assert main(["--setup-hook", "README.md"]) == 2
        assert capsys.readouterr().err == "✖ not inside a git repository\n  hint: run fsg --setup-hook inside your project\n"

    def test_rejects_missing_target(self, tmp_path: Path, capsys, monkeypatch) -> None:
        """Returns 2 and writes no hook when the target file does not exist."""

        init_repository(tmp_path)
        monkeypatch.chdir(tmp_path)
        assert main(["--setup-hook", "READMEE.md"]) == 2
        assert capsys.readouterr().err == "✖ READMEE.md: file not found\n"
        assert not (tmp_path / ".git" / "hooks" / "pre-commit").exists()

    def test_rejects_target_without_markers(self, tmp_path: Path, capsys, monkeypatch) -> None:
        """Returns 2 and leaves an existing pre-commit config unchanged when the target lacks the markers."""

        init_repository(tmp_path)
        (tmp_path / "README.md").write_text("# Title\n", encoding="utf-8")
        config = tmp_path / ".pre-commit-config.yaml"
        config.write_text("repos:\n", encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        assert main(["--setup-hook", "README.md"]) == 2
        assert "missing" in capsys.readouterr().err
        assert config.read_text(encoding="utf-8") == "repos:\n"

    def test_rejects_unsupported_pre_commit_config(self, tmp_path: Path, capsys, monkeypatch) -> None:
        """Returns 2 and leaves the file unchanged when the repos list is not in block style."""

        init_repository(tmp_path)
        write_markers(tmp_path / "README.md")
        config = tmp_path / ".pre-commit-config.yaml"
        config.write_text("repos: []\n", encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        assert main(["--setup-hook", "README.md"]) == 2
        assert config.read_text(encoding="utf-8") == "repos: []\n"
        assert "add the fsg hook manually" in capsys.readouterr().err


@requires_git
class TestGitFailure:
    """Covers errors raised while collecting the paths with git."""

    def test_reports_failing_git(self, tmp_path: Path, capsys, monkeypatch) -> None:
        """Returns 2 and writes nothing when git ls-files fails instead of rendering an empty tree."""

        init_repository(tmp_path)
        readme = write_markers(tmp_path / "README.md")
        monkeypatch.setattr("fsg.git.Git.ls_files", lambda self: (_ for _ in ()).throw(GitError("git ls-files failed: boom")))
        assert main(["--update", str(readme), str(tmp_path)]) == 2
        assert capsys.readouterr().err == "✖ git ls-files failed: boom\n"
        assert readme.read_text(encoding="utf-8") == f"{START_MARKER}\n{END_MARKER}\n"


class TestAsciiOutput:
    """Covers the status symbols with --ascii."""

    def test_uses_bracketed_words(self, tmp_path: Path, capsys) -> None:
        """Replaces the Unicode symbols with bracketed words."""

        create_files(tmp_path, ["main.py"])
        readme = write_markers(tmp_path / "README.md")
        assert main(["--ascii", "--update", str(readme), str(tmp_path)]) == 0
        assert capsys.readouterr().out == f"[ok] {readme}: tree updated\n"
        assert main(["--ascii", "--check", str(tmp_path / "missing.md"), str(tmp_path)]) == 2
        assert capsys.readouterr().err == f"[error] {tmp_path / 'missing.md'}: file not found\n"


class TestInclude:
    """Covers --include on the command line and in the config."""

    def test_shows_only_included_files(self, tmp_path: Path, capsys) -> None:
        """Renders only matching files and their directories."""

        create_files(tmp_path, ["main.py", "README.md", "src/app.py", "docs/guide.md"])
        assert main(["--include", "*.py", "--no-fence", str(tmp_path)]) == 0
        output = capsys.readouterr().out
        assert "main.py" in output
        assert "app.py" in output
        assert ".md" not in output
        assert "docs" not in output

    def test_reads_include_from_config(self, tmp_path: Path) -> None:
        """Applies include patterns from the config in update mode."""

        create_files(tmp_path, ["main.py", "notes.txt"])
        (tmp_path / ".fsg.toml").write_text('include = ["*.py"]\n', encoding="utf-8")
        readme = write_markers(tmp_path / "README.md")
        assert main(["--update", str(readme), str(tmp_path)]) == 0
        text = readme.read_text(encoding="utf-8")
        assert "main.py" in text
        assert "notes.txt" not in text


class TestStyles:
    """Covers --style, --glyph and --summary."""

    def test_renders_style(self, tmp_path: Path, capsys) -> None:
        """Draws the tree with the chosen style."""

        create_files(tmp_path, ["a.py"])
        assert main(["--style", "heavy", "--no-fence", str(tmp_path)]) == 0
        assert "┗━━ a.py" in capsys.readouterr().out

    def test_rejects_unknown_style(self, capsys) -> None:
        """Exits with status 2 for a style that does not exist."""

        with pytest.raises(SystemExit) as exit_info:
            parse_args(["--style", "fancy"])
        assert exit_info.value.code == 2

    def test_applies_glyphs(self, tmp_path: Path, capsys) -> None:
        """Replaces single glyphs given with --glyph."""

        create_files(tmp_path, ["a.py"])
        assert main(["--glyph", "last=*-- ", "--no-fence", str(tmp_path)]) == 0
        assert "*-- a.py" in capsys.readouterr().out

    def test_reports_unequal_glyphs(self, tmp_path: Path, capsys) -> None:
        """Returns 2 with a hint when the glyphs differ in width."""

        assert main(["--glyph", "last=*", str(tmp_path)]) == 2
        assert "same width" in capsys.readouterr().err

    def test_prints_summary(self, tmp_path: Path, capsys) -> None:
        """Adds the summary line with --summary."""

        create_files(tmp_path, ["a.py"])
        assert main(["--summary", "--no-fence", str(tmp_path)]) == 0
        assert capsys.readouterr().out.endswith("0 directories, 1 file\n")


class TestCopy:
    """Covers copying the tree to the clipboard."""

    def test_copies_instead_of_printing(self, tmp_path: Path, capsys, monkeypatch) -> None:
        """Hands the rendered tree to the clipboard and reports it."""

        copied: list[str] = []
        monkeypatch.setattr("fsg.cli.Clipboard.copy", lambda self, text: copied.append(text))
        create_files(tmp_path, ["a.py"])
        assert main(["--copy", str(tmp_path)]) == 0
        assert copied[0].startswith("```plaintext\n")
        assert capsys.readouterr().out == "✔ tree copied to clipboard\n"

    def test_reports_clipboard_error(self, tmp_path: Path, capsys, monkeypatch) -> None:
        """Returns 2 and shows the clipboard error."""

        def fail(self, text: str) -> None:
            raise ClipboardError("no clipboard tool found", "install xclip")

        monkeypatch.setattr("fsg.cli.Clipboard.copy", fail)
        assert main(["--copy", str(tmp_path)]) == 2
        assert capsys.readouterr().err == "✖ no clipboard tool found\n  hint: install xclip\n"

    @pytest.mark.parametrize("mode", ["--update", "--check", "--setup-hook"])
    def test_rejects_copy_with_mode(self, mode: str) -> None:
        """Exits with status 2 when --copy is combined with a mode."""

        with pytest.raises(SystemExit) as exit_info:
            parse_args(["--copy", mode, "README.md"])
        assert exit_info.value.code == 2


class TestSections:
    """Covers several marked blocks with options and kept comments."""

    def test_updates_every_section_with_its_options(self, tmp_path: Path, capsys) -> None:
        """Renders each block with the path and options of its start marker."""

        create_files(tmp_path, ["src/a.py", "docs/guide.md"])
        readme = tmp_path / "README.md"
        readme.write_text(
            "<!-- fsg:start path=src no-op -->\n<!-- fsg:end -->\n".replace(" no-op", "")
            + "<!-- fsg:start path=docs fence=false -->\n<!-- fsg:end -->\n",
            encoding="utf-8",
        )
        assert main(["--update", str(readme)]) == 0
        text = readme.read_text(encoding="utf-8")
        assert "```plaintext\nsrc/\n└── a.py\n```" in text
        assert "-->\ndocs/\n└── guide.md\n<!--" in text
        assert capsys.readouterr().out == f"✔ {readme}: 2 of 2 trees updated\n"

    def test_checks_every_section(self, tmp_path: Path, capsys) -> None:
        """Reports how many blocks are out of date."""

        create_files(tmp_path, ["src/a.py", "docs/guide.md"])
        readme = tmp_path / "README.md"
        readme.write_text(
            "<!-- fsg:start path=src -->\n<!-- fsg:end -->\n<!-- fsg:start path=docs -->\n<!-- fsg:end -->\n",
            encoding="utf-8",
        )
        main(["--update", str(readme)])
        create_files(tmp_path, ["docs/new.md"])
        capsys.readouterr()
        assert main(["--check", str(readme)]) == 1
        assert capsys.readouterr().err.startswith(f"✖ {readme}: 1 of 2 trees are out of date\n")

    def test_keeps_comments_on_update(self, tmp_path: Path) -> None:
        """Re-attaches existing comments and aligns them when a new file appears."""

        create_files(tmp_path, ["src/cli.py"])
        readme = tmp_path / "README.md"
        readme.write_text(
            "<!-- fsg:start path=src fence=false -->\nsrc/\n└── cli.py  # entry point\n<!-- fsg:end -->\n",
            encoding="utf-8",
        )
        create_files(tmp_path, ["src/configuration.py"])
        assert main(["--update", str(readme)]) == 0
        assert readme.read_text(encoding="utf-8") == (
            "<!-- fsg:start path=src fence=false -->\n"
            "src/\n"
            "├── cli.py  # entry point\n"
            "└── configuration.py\n"
            "<!-- fsg:end -->\n"
        )

    def test_check_accepts_commented_tree(self, tmp_path: Path) -> None:
        """Treats a tree with aligned comments as up to date and misaligned ones as out of date."""

        create_files(tmp_path, ["src/cli.py"])
        readme = tmp_path / "README.md"
        readme.write_text(
            "<!-- fsg:start path=src fence=false -->\nsrc/        # code\n└── cli.py  # entry\n<!-- fsg:end -->\n",
            encoding="utf-8",
        )
        assert main(["--check", str(readme)]) == 0
        readme.write_text(
            "<!-- fsg:start path=src fence=false -->\nsrc/  # code\n└── cli.py  # entry\n<!-- fsg:end -->\n",
            encoding="utf-8",
        )
        assert main(["--check", str(readme)]) == 1

    def test_command_line_wins_over_marker(self, tmp_path: Path) -> None:
        """Uses --depth from the command line instead of the marker value."""

        create_files(tmp_path, ["src/gui/a.py"])
        readme = tmp_path / "README.md"
        readme.write_text("<!-- fsg:start path=src depth=1 fence=false -->\n<!-- fsg:end -->\n", encoding="utf-8")
        main(["--update", str(readme), "--depth", "2"])
        assert "a.py" in readme.read_text(encoding="utf-8")

    def test_reports_invalid_marker_option(self, tmp_path: Path, capsys) -> None:
        """Returns 2 and names file and line of the faulty marker."""

        readme = tmp_path / "README.md"
        readme.write_text("text\n<!-- fsg:start colour=red -->\n<!-- fsg:end -->\n", encoding="utf-8")
        assert main(["--check", str(readme), str(tmp_path)]) == 2
        assert f"{readme}:2: unknown marker option 'colour'" in capsys.readouterr().err