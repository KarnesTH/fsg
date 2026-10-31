from importlib.metadata import PackageNotFoundError, version

from fsg.trees import GitProjectTree, PlainProjectTree, ProjectTree

try:
    __version__ = version("fsg")
except PackageNotFoundError:
    __version__ = "unknown"

__all__ = ["GitProjectTree", "PlainProjectTree", "ProjectTree", "__version__"]