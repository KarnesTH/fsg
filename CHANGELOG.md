# Changelog

All notable changes to this project are documented in this file.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-10-31

### Added

- Render a directory as a tree, wrapped in a `plaintext` code fence
- Respect `.gitignore` inside git repositories, skip common generated directories outside of them
- `--depth`, `--dirs-only`, `--exclude` and `--fence`/`--no-fence` to shape the output
- `--ascii` for environments without Unicode support; output is always written as UTF-8
- `--update` and `--check` to keep the tree between `<!-- fsg:start -->` and `<!-- fsg:end -->` up to date
- `--setup-hook` to add fsg to an existing `.pre-commit-config.yaml` or the git `pre-commit` hook
- pre-commit hooks `fsg` and `fsg-check`
- Configuration via `.fsg.toml` or `[tool.fsg]` in `pyproject.toml`
- `--version` and `--help`

[0.1.0]: https://github.com/KarnesTH/fsg/releases/tag/v0.1.0