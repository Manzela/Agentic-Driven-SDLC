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
- Reconciled the specification artifact set to a single canonical state after a verification audit (see `audit/verification-report.md`): 34 Z3 assertions, 22 requirements, 30 correctness properties, 8 Postgres tables, 39 dependency-graph waves, 5 required + 2 optional phases, 6 hooks. Fixed the latent infinite-block HANDOFF defect in the design's Stop-hook reference code (HANDOFF now exits 0, matching Z3 CHECK-5b/5c/8c) and closed every requirement → property → task → wave → CI chain.

### Removed
- Regenerable artifacts excluded from version control: the local virtual environment, byte-compiled caches, and browser-session captures.
