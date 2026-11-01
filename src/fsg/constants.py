DOCS_URL = "https://karnesth.github.io/fsg/"

STYLES = {
    "unicode": {"branch": "├── ", "last": "└── ", "pipe": "│   ", "space": "    "},
    "ascii": {"branch": "|-- ", "last": "`-- ", "pipe": "|   ", "space": "    "},
    "rounded": {"branch": "├── ", "last": "╰── ", "pipe": "│   ", "space": "    "},
    "heavy": {"branch": "┣━━ ", "last": "┗━━ ", "pipe": "┃   ", "space": "    "},
    "double": {"branch": "╠══ ", "last": "╚══ ", "pipe": "║   ", "space": "    "},
}

IGNORED = {
    ".git", ".svn", ".hg",
    ".idea", ".vscode",
    "__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache",
    ".venv", "venv", "env",
    "node_modules", "target", "dist", "build", "out",
    ".godot", ".import",
    ".DS_Store", "Thumbs.db",
    "uv.lock",
}