from pathlib import Path

import pytest

from fsg.cli import main, parse_args
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

    def test_rejects_unknown_options(self) -> None:
        """Exits when an unknown option is given."""

        with pytest.raises(SystemExit):
            parse_args(["--depth", "2"])


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