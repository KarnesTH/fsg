<p align="center">
  <img src="assets/logo.svg" alt="fsg logo" width="128" />
</p>

<h1 align="center">fsg</h1>

<p align="center">
  <img src="https://img.shields.io/badge/version-0.1.0-blue" alt="Version 0.1.0" />
  <img src="https://img.shields.io/badge/python-3.14%2B-3776AB?logo=python&logoColor=white" alt="Python 3.14+" />
  <img src="https://img.shields.io/badge/dependencies-none-brightgreen" alt="No dependencies" />
  <img src="https://img.shields.io/badge/license-MIT-green" alt="MIT License" />
</p>

<p align="center">Prints a project structure as a tree, ready to paste into a GitHub README.</p>

## Features

- Inside a git repository, only files git tracks or would track are listed (`.gitignore` is respected)
- Outside a repository, common generated and tool directories are skipped (`.venv`, `__pycache__`, `node_modules`, `target`, `.idea`, …)
- Directories first, entries sorted case-insensitively, empty directories omitted
- Output is wrapped in a `plaintext` code fence

## Installation

Requires [uv](https://docs.astral.sh/uv/) and git (optional, for `.gitignore` support).

```bash
git clone https://github.com/KarnesTH/fsg.git
cd fsg
uv tool install .
```

## Usage

```bash
fsg [-h] [-V] [path]
```

| Argument          | Description                                         |
|-------------------|-----------------------------------------------------|
| `path`            | Directory to render (default: current directory)    |
| `-h`, `--help`    | Show the help text and exit                         |
| `-V`, `--version` | Show the version and exit                           |

Example:

```bash
fsg src > tree.md
```

```plaintext
src/
└── fsg/
    ├── trees/
    │   ├── __init__.py
    │   ├── git_project_tree.py
    │   ├── plain_project_tree.py
    │   └── project_tree.py
    ├── __init__.py
    ├── __main__.py
    ├── cli.py
    └── constants.py
```

## Development

```bash
uv sync
uv run pytest
```