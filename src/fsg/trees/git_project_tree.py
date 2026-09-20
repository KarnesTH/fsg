import subprocess
from pathlib import Path

from fsg.trees.project_tree import ProjectTree


class GitProjectTree(ProjectTree):
    """Collects the paths git reports as tracked or untracked but not ignored."""

    @staticmethod
    def is_repository(root: Path) -> bool:
        """Returns whether the given path lies inside the working tree of a git repository.

        Args:
            root: Path to check.
        """

        try:
            result = subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
            )
        except (FileNotFoundError, NotADirectoryError):
            return False
        return result.returncode == 0 and result.stdout.strip() == "true"

    def collect(self) -> list[list[str]]:
        """Returns the paths listed by git ls-files, split into their path parts."""

        result = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
            cwd=self.root,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return []
        return [entry.split("/") for entry in result.stdout.split("\0") if entry]