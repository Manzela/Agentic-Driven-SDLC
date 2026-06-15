# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Repository scaffold: git initialization, `.gitignore`, `.env.template`, `pyproject.toml`, and the project documentation suite.
- `verification/` directory housing the Z3 formal-verification harness.
- `.claude/hooks/` and `.claude/agents/` directories reserved for the control-plane implementation.

### Changed
- Established a conventional repository layout. The canonical specification remains under `.kiro/specs/spec-to-evidence-control/`; the reference architecture moved to `docs/reference-architecture/`; the superseded product requirements documents and the deprecated verification harness moved to `docs/superseded/`.

### Removed
- Regenerable artifacts excluded from version control: the local virtual environment, byte-compiled caches, and browser-session captures.
