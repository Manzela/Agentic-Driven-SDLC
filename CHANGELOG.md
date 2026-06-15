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
- Reconciled the specification artifact set to a single canonical state after a verification audit (see `audit/verification-report.md`), then expanded it via the Merge-Reconciliation and P3 Market-Research addenda. Current canonical state: **34 Z3 assertions, 32 requirements, 30 correctness properties, 8 Postgres tables, 49 dependency-graph waves, 57 tasks, 5 required + 2 optional phases, 6 hooks.** The addenda promoted eval-gating, DAST baseline scanning, and an agent kill-switch from deferred to required (Requirements 30–32) and added HANDOFF semantics, amendment versioning, resumed-state integrity, the tamper-evident audit log, performance/accessibility verification, and the structured omission-declaration gate (Requirements 21–29).
- Fixed the latent infinite-block HANDOFF defect in the design's Stop-hook reference code: the HANDOFF triggers (iteration cap, cost budget, no-progress) are evaluated **before** the unproven-items gate and exit 0, matching Z3 CHECK-5b/5c/8c. Every requirement traces to a task and dependency-graph wave; every logic invariant additionally to a correctness property and, where applicable, a Z3 check, while the operational requirements (eval-gating, DAST baseline, kill-switch) trace to required CI status checks rather than Z3 invariants.

### Removed
- Regenerable artifacts excluded from version control: the local virtual environment, byte-compiled caches, and browser-session captures.
