# Plan: Organize the local repo before any coding begins

## Context

`/Users/danielmanzela/Agentic-Driven SDLC` is the working folder for the **Spec-to-Evidence Coverage Control** system — a Claude Code control plane whose canonical spec (`requirements.md` / `design.md` / `tasks.md`) was just reconciled (2026-06-15) and whose 53-task implementation (Kiro `tasks.md`) is about to start. Right now the folder is **not a git repo**, has a **space in its name**, mixes the live spec with superseded PRDs and a deprecated harness at the root, and carries 109 MB of disposable artifacts (`.venv`, `__pycache__`, `.playwright-mcp`, `.DS_Store`).

The goal of this reorg is to turn it into a clean, navigable, git-tracked repo that matches the user's ~15 sibling repos in `~/Professional Profile`, **without front-running structure that `tasks.md` itself owns**. This is preparation only — coding (Kiro task 0 onward) begins after it lands.

Approach was chosen via a 3-lens design panel (pragmatic / convention-aligned / implementation-ready) plus a synthesis pass. Two load-bearing claims were verified directly against the files (see Risks): the canonical harness is **not import-safe**, and the only in-tree reference to the reference-architecture doc is a title citation in `audit/findings.md:5`.

User decisions: repo name = **`spec-to-evidence-control`**; scaffolding altitude = **minimal-plus**; documentation = **full sibling doc suite now**.

## Target structure

```
spec-to-evidence-control/                 # renamed from "Agentic-Driven SDLC" (space removed)
├── .git/                                 # NEW: git init (the single biggest gap vs all siblings)
├── .gitignore                            # NEW (contents below)
├── .env.template                         # NEW: DATABASE_URL, LANGFUSE_*, OTEL_EXPORTER_OTLP_ENDPOINT (never .env)
├── pyproject.toml                        # NEW: source of truth — deps (z3-solver), ruff + pytest config
│
├── README.md                             # NEW: full doc suite (user choice)
├── CHANGELOG.md                          # NEW
├── ROADMAP.md                            # NEW: derived from tasks.md waves 0-44
├── SECURITY.md                           # NEW
├── CONTRIBUTING.md                       # NEW
├── CODE_OF_CONDUCT.md                    # NEW
├── LICENSE                               # NEW: Apache-2.0 (matches siblings — see Assumptions)
│
├── .kiro/                                # KEEP VERBATIM — CANONICAL source of truth (Kiro reads this exact path)
│   └── specs/spec-to-evidence-control/
│       ├── .config.kiro                  # tracked (UUID specId, not a path — rename-safe)
│       ├── requirements.md               # 28 EARS reqs, blocks B01-B19
│       ├── design.md                     # 5-phase arch, 29 properties, hook-wiring table, schemas
│       └── tasks.md                      # 53 tasks (0-52), dependency waves 0-44
│
├── audit/                                # KEEP IN PLACE — forensic trail alongside source (workspace convention)
│   ├── audit-plan.md
│   ├── findings.md                       # line 5 cites "Agentic-Driven SDLC.md" by name → keep that filename
│   └── reconciliation-report.md          # canonical counts: Z3=32, props=29, reqs=28, tasks=53, hooks=6
│
├── verification/                         # NEW home: canonical harness, still SCRIPT-invoked (not packaged)
│   └── formal_verification_merged.py     # MOVED from root — CANONICAL Z3 (32 assertions)
│
├── docs/                                 # NEW: reference + superseded material out of the buildable root
│   ├── reference-architecture/
│   │   └── Agentic-Driven SDLC.md         # MOVED from root, FILENAME UNCHANGED (audit/findings.md cites it)
│   └── superseded/                       # historical-only; README states this is non-authoritative
│       ├── PRD_spec_to_evidence_coverage_control_system.md
│       ├── Kiro's Updated PRD_spec_to_evidence_coverage_control_system.md
│       └── formal_verification.py        # DEPRECATED predecessor (do-not-run banner)
│
├── .claude/                              # NEW (scaffold-light): fixed-location control-plane homes
│   ├── hooks/.gitkeep                    # 6 hooks land here (Kiro tasks fill in)
│   └── agents/.gitkeep                   # Verifier/Initializer/Implementer/Research land here
│
└── tests/.gitkeep                        # NEW: pytest/property tests land here (first testable code)

# DELETED: .venv/ (109M, recreatable), __pycache__/, .playwright-mcp/ (stale 2026-06-15 run), all .DS_Store
# DEFERRED to their own Kiro tasks (NOT created now): the Python package, migrations/, policies/,
#   feature_list.json, .claude/settings.json, .github/ + CI, .pre-commit-config.yaml + .secrets.baseline
```

## File disposition (every current item)

| Current | Action | Destination |
|---|---|---|
| `formal_verification_merged.py` | move | `verification/formal_verification_merged.py` (canonical, stays script-run) |
| `Agentic-Driven SDLC.md` | move (keep filename) | `docs/reference-architecture/Agentic-Driven SDLC.md` |
| `PRD_spec_to_evidence_coverage_control_system.md` | archive | `docs/superseded/` |
| `Kiro's Updated PRD_..._system.md` | archive | `docs/superseded/` (single-quote the apostrophe in `mv`) |
| `formal_verification.py` | archive | `docs/superseded/` (deprecated, do-not-run) |
| `.kiro/` (whole tree) | keep verbatim | unchanged path under renamed root |
| `audit/` (3 files) | keep in place | unchanged path under renamed root |
| `.venv/` | delete | recreatable; **must** go (hardcodes the old absolute path, can't survive rename) |
| `__pycache__/`, `.playwright-mcp/`, all `.DS_Store` | delete | regenerable junk |

## Component homes (where the upcoming Kiro artifacts will live — for reference, not created now)

- **6 hooks** (PreToolUse, PostToolUse, Stop, SubagentStop, PreCompact, SessionStart) → `.claude/hooks/`
- **Subagents** (Verifier, Initializer, Implementer, Research) → `.claude/agents/*.md`
- **`.claude/settings.json`** (hook/agent wiring) → repo root `.claude/`
- **`feature_list.json`** (coverage model) → location + tracked-vs-runtime split decided by its coverage task
- **Postgres migrations 001-008** → `migrations/`
- **OPA/Conftest `.rego`, SAST/Sonar config** → `policies/` + `.github/`
- **OTel / Langfuse / W3C Baggage** → inside the Python package, config via `.env`
- **Python package** → a lowercase_underscore dir (name decided by its task), promoted in `pyproject.toml`
- **Tests** → `tests/` (pytest + `tests/property/`)
- **Harness packaging** → a task to wrap the assertion block in `def main()` + `if __name__` guard, then add `[project.scripts]`

## Documentation standards (binding — all committed markdown)

Every markdown file committed to this repo is treated as **public, enterprise production-grade documentation**, written to survive review by Tier-1 AI-lab / Google-level engineers. This applies to the full doc suite authored in step 10 (`README`, `CHANGELOG`, `ROADMAP`, `SECURITY`, `CONTRIBUTING`, `CODE_OF_CONDUCT`) and to any other `.md` that lands in git history.

Hard rules:
- **No emojis, no decorative badges-as-filler, no marketing/hype adjectives** ("blazing-fast", "revolutionary", "seamless"). Plain, precise, factual prose. Numbers and named technologies carry the weight.
- **No AI-generated tells:** no first-person model voice ("As an AI", "I'll", "Here's your…"), no apologies, no meta-narration, no conversational filler, no "let me…", no placeholder/lorem text, no TODO-to-self notes.
- **No chain-of-thought / internal reasoning leakage** anywhere in docs *or* code comments. Strip any scratch reasoning, "thinking" artifacts, or internal deliberation. Comments explain *what/why* for a maintainer, never narrate a thought process.
- **Active voice, concise, consistent terminology** with the spec (e.g. `Spec_Compiler`, `Coverage_Model`, `Verifier`, `Completion_Gate`). Correct technical typography (real em dashes, straight-vs-curly quotes used consistently).
- **Factual accuracy:** cite the canonical counts from `audit/reconciliation-report.md` (Z3 = 32, properties = 29, requirements = 28, tasks = 53, hooks = 6); every command/code block must be runnable as written.
- `CHANGELOG.md` follows **Keep a Changelog** + SemVer conventions.

Carry-over review (flagged, not auto-edited by this reorg): the pre-existing committed markdown — `docs/reference-architecture/Agentic-Driven SDLC.md`, the three `docs/superseded/` files, and `audit/*.md` — also become public once committed. They must pass the same bar before any public push. **Decision point:** either (a) pass them through the same cleanup, or (b) exclude `docs/superseded/` and `audit/` from the public remote when one is added. Default: keep them committed locally now (no remote yet), review before any push.

## Git strategy + `.gitignore`

`git init -b main` at the renamed root. Sequence guarantees the 109 MB venv is never staged: delete junk → rename → write scaffold + perform moves → `git init` → `git add -A` → `git status --ignored` to confirm staging → single first commit. **Commit only when the user asks**; otherwise stop with a clean staged tree.

`.gitignore` contents:
```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so

# Virtual environments
.venv/
venv/
ENV/

# Distribution / packaging
dist/
build/
*.egg-info/
*.egg

# Testing
.pytest_cache/
htmlcov/
.coverage
.coverage.*
coverage.xml
*.cover

# Type checking
.mypy_cache/
.pyright/

# IDE
.idea/
.vscode/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Claude Code / Playwright MCP — regenerable browser-session artifacts (never source)
.playwright-mcp/

# Secrets — only the template is tracked
.env
.env.*
!.env.template
```

`pyproject.toml` (this reorg): `[project]` metadata (`name = "spec-to-evidence-control"`, `requires-python >= "3.11"`), `dependencies = ["z3-solver==4.16.0"]`, and `[tool.ruff]` / `[tool.pytest.ini_options]` copied from `~/Professional Profile/agent-dag-pipeline/pyproject.toml`. Leave `build-system`, package targets, and `[project.scripts]` to the first package task (no package exists yet).

## Migration steps (ordered)

0. **Pre-flight (read-only):** confirm no terminal/editor/Claude session has cwd inside the folder; `cd /Users/danielmanzela`.
1. **Pre-flight grep (read-only):** already verified — only `audit/findings.md:5` cites the doc name; `audit/` has no `.playwright-mcp` dependency; not a git repo.
2. **Capture dep (optional):** confirm `z3-solver==4.16.0` is the only top-level dep (`pip freeze | grep -i z3` inside the venv) before deleting it.
3. **Delete junk in place:** `rm -rf .venv __pycache__ .playwright-mcp` and `find . -name .DS_Store -delete` (shrinks 111 MB → ~2 MB; ensures git never sees the venv).
4. **Rename folder:** `mv '/Users/danielmanzela/Agentic-Driven SDLC' /Users/danielmanzela/spec-to-evidence-control`.
5. **Create dirs:** `mkdir -p verification docs/reference-architecture docs/superseded .claude/hooks .claude/agents tests`.
6. **Move harness:** `formal_verification_merged.py` → `verification/`.
7. **Move reference doc (name unchanged):** `Agentic-Driven SDLC.md` → `docs/reference-architecture/`.
8. **Archive superseded/deprecated:** the two PRDs + `formal_verification.py` → `docs/superseded/` (single-quote the apostrophe path).
9. **Track empty dirs:** `touch .claude/hooks/.gitkeep .claude/agents/.gitkeep tests/.gitkeep`.
10. **Write scaffold:** `.gitignore`, `.env.template`, `pyproject.toml`, and the full doc suite (`README`, `CHANGELOG`, `ROADMAP`, `SECURITY`, `CONTRIBUTING`, `CODE_OF_CONDUCT`, `LICENSE`). **All authored markdown must meet the Documentation standards section above** (no emojis, no AI tells, no CoT leakage, enterprise-grade). README states `docs/superseded/` is non-authoritative and documents how to run the harness.
11. **Smoke-test before git:** `python3 verification/formal_verification_merged.py` → expect exit 0, "All 32 checks passed".
12. **`git init -b main`**, `git add -A`, then `git status --ignored` to confirm `.kiro/`, `.config.kiro`, `audit/`, `verification/`, `docs/`, the `.gitkeep`s, and the scaffold files are staged while `.venv/.playwright-mcp/__pycache__/.env/.DS_Store` are ignored. Add `!.kiro/` / `!.config.kiro` negations only if a global gitignore swallowed them.
13. **First commit (only if user asks):** `git commit -m "chore: initial commit — reconciled spec, audit, and canonical Z3 harness (reorg from flat folder)"`.
14. **Hand off:** implementation proceeds from `.kiro/specs/spec-to-evidence-control/tasks.md`.

## Risks & mitigations

- **Harness is not import-safe** (verified: top-level `check(...)` calls, bare `sys.exit`, no `main()`/`__name__` guard). → Keep it script-invoked; do **not** package it. Packaging is a deferred Kiro task.
- **Don't move the Kiro spec** (a rejected lens proposed `docs/spec/` + symlinks). → `.kiro/` stays verbatim; it's the canon and Kiro reads it by path.
- **Don't rename `Agentic-Driven SDLC.md`** (verified: cited by name in `audit/findings.md:5`). → Move it but keep the filename byte-for-byte.
- **`.venv` deletion / Python version** → confirmed working with `z3-solver==4.16.0`; recreate with `python3 -m venv .venv && pip install z3-solver==4.16.0` (pin `requires-python >= 3.11`).
- **Apostrophe/space in the "Kiro's Updated…" filename** → single-quote the source path in `mv`.
- **Global gitignore swallowing dotfiles** → verify with `git status --ignored`; add explicit negations if needed.

## Verification

1. **Harness unbroken from new path:** `python3 verification/formal_verification_merged.py` → exit 0, "All 32 checks passed".
2. **Junk gone:** `du -sh .` ≈ 2 MB; no `.venv` / `__pycache__` / `.playwright-mcp`; `find . -name .DS_Store` empty.
3. **Canon intact:** `.kiro/specs/spec-to-evidence-control/{.config.kiro,requirements.md,design.md,tasks.md}` all present and unchanged.
4. **Git tracks the right set:** `git status --ignored` matches the strategy above; working tree clean after commit.
5. **No new broken refs:** `grep -rIn 'Agentic-Driven SDLC'` → only the `audit/findings.md` title citation of the (same-named, now relocated) doc.
6. **Tree matches** the target above (`find . -maxdepth 3` / `tree -a -L 3`); folder resolves unquoted (`cd /Users/danielmanzela/spec-to-evidence-control`).

## Assumptions

- **LICENSE = Apache-2.0**, matching `agent-dag-pipeline` / `Antigravity-OS`. Change if this repo should differ.
- **`ROADMAP.md`** is derived from `tasks.md` waves 0-44; **`SECURITY.md` / `CONTRIBUTING.md` / `CODE_OF_CONDUCT.md`** use standard sibling boilerplate adapted to this repo.
- **No remote / no push** as part of this reorg — that's a later, explicit decision.
- **Security tooling** (`.pre-commit-config.yaml`, `.secrets.baseline`) and **CI** are deferred to their Kiro tasks (they need real content + a baseline scan; gating an empty repo adds nothing now).
