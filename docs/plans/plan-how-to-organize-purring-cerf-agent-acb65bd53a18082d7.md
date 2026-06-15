# Reorg Plan — CONVENTION-ALIGNED lens

Target: `/Users/danielmanzela/Agentic-Driven SDLC` → rename to `spec-to-evidence-control`
Make it look like `agent-dag-pipeline` / `Antigravity-OS`: hatchling pyproject, lowercase_underscore
package (`spec_to_evidence/`), tests/, docs/, .github/, full doc suite, .env.template, .gitignore,
.pre-commit-config + .secrets.baseline (security-conscious).

Canonical package: `spec_to_evidence/`
CLI script: `spec-evidence = "spec_to_evidence.__main__:main"`
Z3 harness becomes a runnable module: `spec_to_evidence/verification/formal.py` (entry `spec-evidence verify`).

Key moves:
- formal_verification_merged.py → spec_to_evidence/verification/formal.py (canonical)
- formal_verification.py → docs/history/formal_verification_deprecated.py (archive)
- .kiro/specs/spec-to-evidence-control/{requirements,design,tasks}.md → docs/spec/ (mirror via symlink so Kiro still resolves)
- Agentic-Driven SDLC.md → docs/reference-architecture.md
- PRD + Kiro PRD → docs/history/ (superseded)
- audit/ stays at root (sibling convention: audit/ alongside source)
- .playwright-mcp, .venv, __pycache__ → gitignored / deleted

See structured output for the full spec.
