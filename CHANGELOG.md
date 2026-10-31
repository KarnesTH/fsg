# Changelog

All notable changes to this project are documented in this file.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/).

## [0.2.0] - 2026-10-31

### Changed

- Status lines start with a symbol (`✔`, `•`, `✖`, or `[ok]`, `[info]`, `[error]` with `--ascii`), are colored in terminals and show a hint on how to fix a problem; `NO_COLOR` and `FORCE_COLOR` are respected
- Every error exits with status 2, including a path that is not a directory; status 1 only means an outdated tree
- The search for a config file stops at the git repository root, or at the home directory outside a repository
- Indented code blocks and longer code fences are recognized when looking for the markers

### Fixed

- Tracked files deleted from the working tree no longer appear in the tree
- `--setup-hook` adds the fsg step before a final `exec` line of an existing git hook
- An existing pre-commit entry is detected by its `repo:` line, so comments or similarly named repositories no longer block the setup
- `--version` and `--setup-hook` work when fsg runs from a source checkout without being installed

## [0.1.1] - 2026-10-31

### Security

- Resolve the git executable from absolute PATH entries only, so a `git.exe` inside the current directory is never run on Windows
- Quote the target file in the message of the generated git hook, so shell syntax in the file name is not executed
- Reject a configured `path` that leaves the directory of the config file

### Fixed

- `--update` no longer overwrites content when the end marker is missing: both markers must stand on their own line outside a code block
- `--setup-hook` checks that the target file exists and holds both markers before writing a hook
- Files are written atomically, so an interrupted run cannot leave a half-written README or hook
- A failing `git ls-files` is reported instead of producing an empty tree

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

[0.2.0]: https://github.com/KarnesTH/fsg/releases/tag/v0.2.0
[0.1.1]: https://github.com/KarnesTH/fsg/releases/tag/v0.1.1
[0.1.0]: https://github.com/KarnesTH/fsg/releases/tag/v0.1.0