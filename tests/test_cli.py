from pathlib import Path

from fsg.cli import main
from tests.conftest import create_files


class TestMain:
    """Covers the command line entry point."""

    def test_prints_tree_for_given_path(self, tmp_path: Path, capsys) -> None:
        """Writes the tree of the path passed as the first argument to stdout."""

        create_files(tmp_path, ["__main__.py"])
        assert main([str(tmp_path)]) == 0
        assert "__main__.py" in capsys.readouterr().out

    def test_uses_current_directory_without_arguments(self, tmp_path: Path, capsys, monkeypatch) -> None:
        """Renders the current working directory when no argument is given."""

        create_files(tmp_path, ["__main__.py"])
        monkeypatch.chdir(tmp_path)
        assert main([]) == 0
        output = capsys.readouterr().out
        assert f"{tmp_path.name}/" in output
        assert "__main__.py" in output

    def test_reads_command_line_arguments(self, tmp_path: Path, capsys, monkeypatch) -> None:
        """Falls back to sys.argv when no argument list is passed."""

        create_files(tmp_path, ["__main__.py"])
        monkeypatch.setattr("sys.argv", ["fsg", str(tmp_path)])
        assert main() == 0
        assert "__main__.py" in capsys.readouterr().out

    def test_ignores_further_arguments(self, tmp_path: Path, capsys) -> None:
        """Uses the first argument only."""

        create_files(tmp_path, ["__main__.py"])
        assert main([str(tmp_path), str(tmp_path / "missing")]) == 0
        assert "__main__.py" in capsys.readouterr().out

    def test_reports_missing_directory(self, tmp_path: Path, capsys) -> None:
        """Writes an error to stderr and returns 1 when the path does not exist."""

        assert main([str(tmp_path / "missing")]) == 1
        assert "not a directory" in capsys.readouterr().err

    def test_reports_file_instead_of_directory(self, tmp_path: Path, capsys) -> None:
        """Writes an error to stderr and returns 1 when the path is a file."""

        create_files(tmp_path, ["__main__.py"])
        assert main([str(tmp_path / "__main__.py")]) == 1
        assert "not a directory" in capsys.readouterr().err