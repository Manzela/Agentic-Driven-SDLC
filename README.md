# Agentic-Driven SDLC Platform

**An autonomous Spec-to-Evidence SDLC control plane on Claude Code — intent in, verified software out, completion decided by deterministic gates instead of model self-assessment.**

This repository is an end-to-end software-delivery control plane: a fleet of Claude Code agents (memory, verifier, scope-enforcer, auditor) compiles a specification into tracked coverage items, drives implementation, and is held to a **fail-closed completion gate** that refuses to report "done" until every in-scope requirement is backed by a recorded evidence artifact and every deterministic check passes. It ships with a self-hosted [Plane](https://plane.so) project-management control plane so the same governed workflow is visible and steerable as live work items.

The governing invariant: **completion is decided by deterministic gates, not by a model's claim that it finished.**

---

## The two halves

The platform is one system with two cooperating control planes.

| Half | What it is | Where it lives |
|---|---|---|
| **Spec-to-Evidence engine** | The execution and enforcement layer. 26 Python tool-modules (compilers, verifiers, gates, durable store, orchestrator) plus 6 Claude Code hooks and 4 agents that turn a spec into verified, evidence-backed delivery. Enforcement runs in the hooks, not in model judgment. | `tools/`, `.claude/`, `db/` |
| **Plane PM control plane** | A self-hosted Plane workspace (13-service Docker stack) that materializes the same spec as live work items and runs the agent loop over the REST API + webhooks. A 12-state agent workflow mirrors the engine's gate ordering — only the verifier, with complete evidence, may set `Done`. | `plane-integration/`, `plane-selfhost/` |

The engine is the source of truth for *what counts as done*; Plane is where that truth becomes a navigable board.

### How enforcement actually happens

Six Claude Code hooks (`PreToolUse`, `PostToolUse`, `Stop`, `SubagentStop`, `PreCompact`, `SessionStart`) wire deterministic checks directly into the agent runtime:

- a **coverage model** tracks each requirement's status and its evidence;
- a **Stop-gate** refuses completion while any in-scope item is unproven (and HANDOFFs — not loops — on iteration cap, cost budget, or no-progress);
- an **evidence schema** requires a complete four-field `Evidence_Record` before any item can transition to `proven`, and only the verifier (never the implementer) may capture it;
- an **append-only coverage guard** blocks deletion, truncation, or reorder of tracked items;
- a **resume-integrity gate** blocks a resumed run whose durable state hash does not match;
- a **tamper-evident audit log** hash-chains every gate decision.

---

## The three locked phases

The delivery lifecycle is modeled as three locked phases. Phases 0–6 of the build are complete, tested, and on `main`.

| Phase | Name | What it guarantees |
|---|---|---|
| **1** | **Intent → Spec** | An intent is compiled into EARS requirements, enriched by proactive discovery against a human-approved, fact-checked domain-baseline checklist, and validated for contradictions, ambiguities (vague-adjective scan), and coverage before any code is written. |
| **2** | **Spec → Verified Delivery** | Each requirement becomes an in-scope coverage item; an implementer produces a slice and a separate verifier proves it; wiring, orphan, and append-only checks run continuously; durable Postgres state and supply-chain/security gates keep the run honest and resumable. |
| **3** | **Delivery → Proof** | Completion is gated on machine-checked proof: the formal-verification harness, the property + spine test suite, the zero-evidence coverage gate, secrets diff-scan, and DAST baseline must all be green before a merge to `main` is permitted. |

---

## What it replaces

| Instead of… | This platform provides… |
|---|---|
| An agent that *says* it finished | A fail-closed completion gate that refuses to report done until every in-scope item carries recorded evidence |
| "Looks done to me" self-assessment | Deterministic checks wired into hooks — the CI verdicts are the gate, no self-report is accepted |
| Requirements that drift from code | A spec → coverage-item → evidence → audit-log traceability chain, durable in Postgres |
| Manual PR gatekeeping and review checklists | 5 required, non-bypassable status checks enforced as GitHub branch protection on `main` |
| Implementers grading their own work | Hard role separation — the implementer never self-verifies; only the verifier captures evidence and sets `Done` |
| A spreadsheet or wiki of project status | A self-hosted Plane board where the live spec, coverage, and agent state are first-class work items |

---

## Status

| Signal | State |
|---|---|
| Branch | Built on `main` behind **5 required CI checks** |
| Phases | **0–6 complete** (verification, durable state, security, proof, durable orchestration, predictive routing) |
| Formal harness | **34 / 34** Z3 assertions passing |
| Test suite | **254 tests** collected (spine, property, integration) |
| Pull requests | **7 merged** |
| CI | **Green** |

The completion gate is real: a PR can only reach `main` when the Z3 harness (34/34), the property + spine suite, the zero-evidence coverage gate, the gitleaks secrets diff-scan, and the OWASP ZAP baseline are all green. See [`docs/github-ruleset.md`](docs/github-ruleset.md).

---

## Quick start

Requires Python ≥ 3.11. Docker is needed only for the Plane control plane.

```bash
# 1. Clone
git clone https://github.com/Manzela/Agentic-Driven-SDLC.git
cd Agentic-Driven-SDLC

# 2. Virtual environment + dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install z3-solver==4.16.0.0 pytest hypothesis

# 3. Run the formal-verification harness
#    Passing run prints "Result: 34/34 checks passed" and exits 0.
python verification/formal_verification_merged.py

# 4. Run the test suite (254 tests: spine + property + integration)
pytest
```

### Deploy the Plane PM control plane

```bash
cd plane-selfhost
# plane.env is pre-configured: LISTEN_HTTP_PORT=8090, APP_DOMAIN=localhost:8090
docker compose --env-file plane.env up -d        # 13 services; web on http://localhost:8090
```

### Provision the workspace from the spec

```bash
cd plane-integration
python3 provision_plane.py all     # idempotent; external_id-keyed, safe to re-run
python3 the_loop.py status         # work items across the 12 agent-workflow states
python3 the_loop.py next           # highest-priority actionable item for an agent
```

`the_loop.py` exposes the completion-gate-ordered PM interface (`status` / `next` / `advance` / `prove` / `handoff`); `prove <id> <test_file> <test_name> <output_hash>` attaches the four-field `Evidence_Record` and sets `Done` — only via the verifier, with complete evidence.

Copy `.env.template` to `.env` for the durable-storage (`DATABASE_URL`), Langfuse, and OpenTelemetry settings the engine reads at runtime.

---

## Repository map

```
.kiro/                  Canonical specification (source of truth)
  specs/spec-to-evidence-control/
    requirements.md       32 EARS requirements
    design.md             Architecture, 32-component inventory, correctness
                          properties, hook-wiring table, 8 data schemas
    tasks.md              57 phased tasks across the dependency-graph waves
tools/                  26 engine modules — spec compiler/validator, wiring &
                        orphan detectors, coverage/eval/perf-a11y gates,
                        traceability writer, durable store, audit log,
                        durable orchestrator, predictive router, kill-switch
.claude/                Control-plane runtime
  hooks/                  6 hooks (PreToolUse … SessionStart) — where the gates fire
  agents/                 implementer, verifier, research, initializer
  settings.json           Hook wiring
db/migrations/          8 Postgres migrations (requirements → coverage → evidence
                        → run_state → audit log)
tests/                  254 tests — spine (unit), property (Hypothesis), integration
plane-integration/      Provisioner, agent⇄Plane client, webhook handler, the_loop
plane-selfhost/         Plane v1 community stack (docker-compose)
docs/                   Architecture, board guide, component map, ruleset, plane blueprint
.github/workflows/      CI: harness, coverage-gate, secrets-scan, zap-baseline
```

---

## Documentation

| Document | What it covers |
|---|---|
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | System architecture: the engine, the hooks, the gate model, durable state, and the three locked phases end to end |
| [`docs/plane/BOARD_GUIDE.md`](docs/plane/BOARD_GUIDE.md) | Navigating the live Plane board — modules, cycles, views, the 12-state agent workflow, and how to drive the loop |
| [`docs/COMPONENT_MAP.md`](docs/COMPONENT_MAP.md) | Every component mapped to its requirement, correctness property, hook, and test |
| [`docs/github-ruleset.md`](docs/github-ruleset.md) | The enforced `main`-branch completion gate: the 5 required status checks and how to harden them to the full spec posture |

Supporting docs: [`CONTRIBUTING.md`](CONTRIBUTING.md) (workflow and documentation standards), [`SECURITY.md`](SECURITY.md) (policy and reporting), [`ROADMAP.md`](ROADMAP.md) (phased delivery), [`CHANGELOG.md`](CHANGELOG.md) (release history). The full Plane specification lives in [`docs/plane/PLANE_BLUEPRINT.md`](docs/plane/PLANE_BLUEPRINT.md).

---

## License

Apache-2.0. See [`LICENSE`](LICENSE).
