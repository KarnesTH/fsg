from fsg.git import Git
from fsg.trees.project_tree import ProjectTree


class GitProjectTree(ProjectTree):
    """Collects the paths git reports as tracked or untracked but not ignored."""

    def collect(self) -> list[list[str]]:
        """Returns the paths listed by git ls-files, split into their path parts.

        Raises:
            OSError: git cannot run or the command fails.
        """

        return [entry.split("/") for entry in Git(self.root).ls_files()]