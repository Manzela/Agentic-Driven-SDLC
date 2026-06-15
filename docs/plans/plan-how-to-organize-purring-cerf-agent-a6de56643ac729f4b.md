# Reorg plan — Agentic-Driven SDLC → spec-to-evidence-control

## Verified facts (from disk, not just inventory)
- 111M total, 109M is .venv (Python 3.14), 2.0M .playwright-mcp (27 files).
- `.config.kiro` = `{"specId":"0f7e003f-...","workflowType":"requirements-first","specType":"feature"}` — a UUID, NOT a path. Folder rename is safe for Kiro.
- `formal_verification_merged.py` is self-contained (no file IO, no hardcoded paths), self-counts assertions (`TOTAL = checks_run`, 32). BUT it executes at module top-level and ends with a bare `sys.exit()` — there is NO `def main()` and NO `if __name__` guard. Importing it = running it + exiting. → keep it script-invoked; defer package-ification to a coding task.
- Only ONE "Agentic-Driven SDLC" string in tracked content: `audit/findings.md:5`, citing the *document* as reference architecture (not a path). → rename folder yes; rename the .md no.
- `formal_verification.py` has an explicit DEPRECATED banner ("Do NOT run this in CI or cite its count").
- Sibling `agent-dag-pipeline`: hyphenated repo, `agent_dag/` package, full doc suite, `.env.example`, standard Python `.gitignore`.
- `.DS_Store` lives at `.kiro/specs/.DS_Store`.

## Decision summary
- RENAME folder via `git mv` AFTER `git init` (so the rename is in history) — actually: rename dir first with `mv`, then `git init`, so history starts clean under final name. New name: `spec-to-evidence-control` (matches the spec id + .kiro dir; the product identity, not the essay title).
- Hybrid repo: Python-package repo AND Claude-Code-config repo. `.claude/` and the package coexist — siblings already do this.
- Scaffold the homes the FIRST waves of tasks.md need (verification/, .claude/, tests/, docs/, archive); defer migrations/policies/sec-package internals until their tasks.
- README + CHANGELOG now; full doc suite deferred (not a showcase repo yet).
- Keep .kiro spec in place (canonical), keep audit/ in place, archive superseded PRDs + deprecated harness, delete venv/caches/playwright/DS_Store.
