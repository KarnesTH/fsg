import io
from importlib.metadata import version
from pathlib import Path

import pytest

from fsg.cli import main, parse_args
from fsg.readme_section import END_MARKER, START_MARKER
from tests.conftest import create_files


class TestParseArgs:
    """Covers the argument parsing."""

    def test_reads_path_argument(self) -> None:
        """Returns the given path as a Path object."""

        assert parse_args(["src"]).path == Path("src")

    def test_defaults_to_current_directory(self) -> None:
        """Returns the current directory when no path is given."""

        assert parse_args([]).path == Path(".")

    def test_rejects_further_arguments(self) -> None:
        """Exits when more than one path is given."""

        with pytest.raises(SystemExit):
            parse_args(["src", "tests"])

    def test_ascii_defaults_to_false(self) -> None:
        """Returns False for use_ascii when the option is not given."""

        assert parse_args([]).use_ascii is False

    def test_reads_ascii_option(self) -> None:
        """Returns True for use_ascii when --ascii is given."""

        assert parse_args(["--ascii"]).use_ascii is True

    def test_render_options_default(self) -> None:
        """Returns no depth, all entries, no exclusions and an enabled fence when no option is given."""

        args = parse_args([])
        assert (args.depth, args.dirs_only, args.exclude, args.fence) == (None, False, [], True)

    def test_reads_render_options(self) -> None:
        """Reads depth, dirs-only, repeated excludes and no-fence."""

        args = parse_args(["-d", "2", "--dirs-only", "-e", "*.log", "--exclude", "tests", "--no-fence"])
        assert (args.depth, args.dirs_only, args.exclude, args.fence) == (2, True, ["*.log", "tests"], False)

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

        assert main([str(tmp_path / "missing")]) == 1
        assert "not a directory" in capsys.readouterr().err

    def test_reports_file_instead_of_directory(self, tmp_path: Path, capsys) -> None:
        """Writes an error to stderr and returns 1 when the path is a file."""

        create_files(tmp_path, ["main.py"])
        assert main([str(tmp_path / "main.py")]) == 1
        assert "not a directory" in capsys.readouterr().err

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
        assert capsys.readouterr().out.strip() == f"fsg {version('fsg')}"
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
        """Writes the rendered tree between the markers and reports the change on stderr."""

        create_files(tmp_path, ["main.py"])
        readme = tmp_path / "README.md"
        readme.write_text(f"# Title\n{START_MARKER}\n{END_MARKER}\n", encoding="utf-8")
        assert main(["--update", str(readme), str(tmp_path)]) == 0
        text = readme.read_text(encoding="utf-8")
        assert "── main.py" in text
        assert text.startswith(f"# Title\n{START_MARKER}\n```plaintext\n")
        captured = capsys.readouterr()
        assert captured.out == ""
        assert "updated" in captured.err

    def test_update_is_silent_when_current(self, tmp_path: Path, capsys) -> None:
        """Writes nothing to stderr when the section is already current."""

        create_files(tmp_path, ["main.py"])
        readme = tmp_path / "README.md"
        readme.write_text(f"{START_MARKER}\n{END_MARKER}\n", encoding="utf-8")
        main(["--update", str(readme), str(tmp_path)])
        capsys.readouterr()
        assert main(["--update", str(readme), str(tmp_path)]) == 0
        assert capsys.readouterr().err == ""

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
        assert "out of date" in capsys.readouterr().err

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
        assert "missing" in capsys.readouterr().err

    @pytest.mark.parametrize("option", ["--update", "--check"])
    def test_reports_missing_file(self, option: str, tmp_path: Path, capsys) -> None:
        """Returns 2 and reports the error on stderr when the file does not exist."""

        assert main([option, str(tmp_path / "MISSING.md"), str(tmp_path)]) == 2
        assert "MISSING.md" in capsys.readouterr().err