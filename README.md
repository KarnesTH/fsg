<p align="center">
  <img src="https://raw.githubusercontent.com/KarnesTH/fsg/main/assets/logo.svg" alt="fsg logo" width="128" />
</p>

<h1 align="center">fsg</h1>

<p align="center">
  <img src="https://img.shields.io/badge/version-0.5.0-blue" alt="Version 0.5.0" />
  <img src="https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white" alt="Python 3.11+" />
  <img src="https://img.shields.io/badge/dependencies-none-brightgreen" alt="No dependencies" />
  <img src="https://img.shields.io/badge/license-MIT-green" alt="MIT License" />
</p>

<p align="center">Generates clean directory trees that respect .gitignore and keep your docs up to date.</p>

<p align="center">
  <a href="https://karnesth.github.io/fsg/">Documentation</a> · <a href="https://karnesth.github.io/fsg/de/">Dokumentation</a> · <a href="https://karnesth.github.io/fsg/changelog/">Changelog</a>
</p>

<p align="center">
  <img src="https://raw.githubusercontent.com/KarnesTH/fsg/main/docs/demo.gif" alt="fsg demo" />
</p>

## Features

- Respects `.gitignore` inside a git repository and skips tool directories like `.venv` or `node_modules` outside
- Keeps marked trees in your README up to date, with a check mode for CI
- Comments next to entries survive every update
- Several trees per file, each with its own options
- Sets up a pre-commit or git hook for you
- Depth, directories only, include and exclude filters, built-in styles or your own glyphs
- No dependencies, pure Python 3.11+

## Installation

```bash
uv tool install fsg   # or: pipx install fsg
uvx fsg               # run without installing
```

## Quickstart

Add the markers where the tree should appear:

```markdown
<!-- fsg:start -->
<!-- fsg:end -->
```

```bash
fsg --update README.md       # writes the tree between the markers
fsg --check README.md        # exit 1 if the tree is out of date
fsg --setup-hook README.md   # updates the tree on every commit
```

This is the tree of this repository, rendered with `[tool.fsg]` from `pyproject.toml`:

<!-- fsg:start -->
```plaintext
src/
└── fsg/
    ├── hooks/            # commit hook setup
    ├── trees/            # git and plain directory walk
    ├── __init__.py
    ├── __main__.py
    ├── cli.py            # arguments and modes
    ├── clipboard.py      # --copy
    ├── config.py         # .fsg.toml and [tool.fsg]
    ├── console.py        # status lines
    ├── constants.py      # styles and ignored names
    ├── errors.py         # errors with hints
    ├── executable.py     # safe PATH lookup
    ├── git.py            # git commands
    ├── glyphs.py         # tree styles
    ├── marked_file.py    # marker blocks
    ├── section.py        # marker options
    ├── text_file.py      # atomic UTF-8 writes
    └── tree_comments.py  # comments kept on update
```
<!-- fsg:end -->

## Documentation

`fsg --docs` opens the documentation in your browser. It is available in [English](https://karnesth.github.io/fsg/) and [German](https://karnesth.github.io/fsg/de/):

- [Installation](https://karnesth.github.io/fsg/installation/) – uv, pipx and uvx
- [Usage](https://karnesth.github.io/fsg/usage/) – every option, filters and exit codes
- [Markers & sections](https://karnesth.github.io/fsg/markers/) – one or several trees per file, comments and hooks
- [Configuration](https://karnesth.github.io/fsg/configuration/) – `.fsg.toml` and `[tool.fsg]`
- [Styles](https://karnesth.github.io/fsg/styles/) – built-in styles, own glyphs and the summary line
- [Recipes](https://karnesth.github.io/fsg/recipes/) – CI checks, pre-commit and monorepos

## Development

```bash
git clone https://github.com/KarnesTH/fsg.git
cd fsg
uv sync
uv run pytest
```