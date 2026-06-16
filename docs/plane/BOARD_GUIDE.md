# ASCP Plane Board — Navigation & Onboarding Guide

> Read this first. In ten minutes it takes a zero-context viewer from "what am I looking at" to fluent navigation of the Agentic SDLC Control Plane (`ASCP`) board.

**Live board:** `http://localhost:8090` · workspace **`ascp`** · project **`ASCP`** (Agentic SDLC Control Plane)
**Start Here:** the **ASCP — Start Here** onboarding page, linked from the project sidebar (Pages). It is the human entry point; this guide is its long form.
**Source of record:** the board is generated from `.kiro/specs/spec-to-evidence-control` and `docs/plane/plane_backlog.json`. Configuration is reproducible via `plane-integration/provision_plane.py`.

---

## 1. The mission

ASCP is an autonomous **Spec-to-Evidence SDLC control plane**: it takes product intent and produces verified software — *intent → verified software* — with software agents acting as memory, verifier, scope-enforcer, and auditor, and a **fail-closed completion gate** that refuses to call anything "done" without evidence.

The Plane board you are reading is the **PM control plane**: the human-facing surface where every coverage item, gate decision, agent run, and human handoff is visible as a Plane **work item (issue)** moving through a 12-state agent lifecycle. The board does **not** decide completion. The deterministic gates do that — Claude Code Stop/PreToolUse/PostToolUse hooks, OPA policy, and five required CI checks on `main`.

> **The one rule that governs everything here:** Plane is a *projection* of gate decisions, never a substitute for them. A work item reaching **Done** on the board is the *shadow* of a real Stop + OPA + CI pass in Postgres. If a human drags an unproven item to **Done**, the system reverts it. **Postgres is authoritative; Plane mirrors it.**

Two layers run in parallel:

| Layer | What it is | Where it is |
|---|---|---|
| **Enforcement** | The real gates: Claude Code hooks, OPA/Conftest, GitHub required CI checks | repo `.claude/hooks`, `.github/workflows`, GitHub ruleset on `main` |
| **Governance (this board)** | A queryable mirror of where each item is and who may move it next | Plane project `ASCP` |

---

## 2. The 12-state agent lifecycle (legend)

Every work item is an agent run through a 12-state machine. The states map onto Plane's five state-groups (`backlog | unstarted | started | completed | cancelled`). The four `cancelled`-group states are the platform's **non-Done terminal states** — `HANDOFF`, `Blocked`, and `Failed` are deliberately distinct from each other and from `Done`. A HANDOFF run is *never* marked complete.

| # | State | Plane group | What it means | Who moves it in (authority) |
|---|---|---|---|---|
| 1 | **Backlog** | backlog | Unrefined intake; not yet classified | system / human (creation) |
| 2 | **Agent-Triaged** | unstarted | Classified; `agent_role` + `requirement_id` assigned | `initializer` (or `research` for context sourcing) |
| 3 | **Spec-Compiling** | started | Initializer compiling EARS + running `spec_validator` (Z3) | `initializer` |
| 4 | **Spec-Verified** | started | `violation_count == 0`; `feature_list.json` emitted (all items unproven) | `initializer` |
| 5 | **Plan-Approved** | started | **Human** plan approval written (`plan-approved.json`, SHA-bound to `feature_list.json`) | **`human` only** |
| 6 | **Agent-Executing** | started | Implementer building **one** slice in an isolated git worktree | `implementer` |
| 7 | **In-Verification** | started | Verifier running 5-layer checks; capturing the Evidence_Record | `verifier` |
| 8 | **Human-Review** | started | PR open + **human** reviewer gate | `verifier` advances *into*; `human` acts on it |
| 9 | **Done** | completed | Proven with evidence; all gates (Stop + OPA + CI) pass | **`human` only** (the PR-review edge) |
| 10 | **HANDOFF** | cancelled | Cap / budget / no-progress reached; handed to a human (distinct from Done) | `verifier` / `human` reconciliation |
| 11 | **Blocked** | cancelled | A gate blocked (exit 2): unproven dependency, failed integrity/approval | `verifier` (gate decision) |
| 12 | **Failed** | cancelled | Verification failed; evidence withheld | `verifier` (gate decision) |

### State-machine diagram

```
                                  ┌─────────────────────────── human only ───────────────────────────┐
                                  │                                                                    │
  ┌─────────┐    ┌──────────────┐ │  ┌───────────────┐    ┌──────────────┐    ┌──────────────┐         │
  │ Backlog │──▶ │ Agent-Triaged│─┼─▶│ Spec-Compiling│──▶ │ Spec-Verified│──▶ │ Plan-Approved│         │
  └─────────┘    └──────────────┘ │  └───────────────┘    └──────────────┘    └──────┬───────┘         │
   intake          initializer    │     initializer        Z3 clean,            human writes            │
                   / research      │    (EARS + Z3)        feature_list.json     plan-approved.json      │
                                   │                       (all unproven)              │                 │
                                   └───────────────────────────────────────────────── │ ────────────────┘
                                                                                       ▼
                                                                              ┌──────────────────┐
                                                                              │  Agent-Executing │  implementer:
                                                                              └────────┬─────────┘  one slice,
                                                                                       │            one worktree,
                                                                                       ▼            one commit
                                                                              ┌──────────────────┐
                                                                              │  In-Verification │  verifier:
                                                                              └───┬────┬─────┬───┘  5-layer checks
                                                          ┌───────────────────────┘    │     └───────────────────┐
                                                          ▼ (5 layers pass,            ▼ (evidence              ▼ (cap/budget/
                                                  ┌──────────────┐  coverage ≥85%) ┌────────┐  withheld)   ┌──────────┐ no-progress)
                                                  │ Human-Review │                 │ Failed │              │ HANDOFF  │
                                                  └──────┬───────┘                 └────────┘              └──────────┘
                                                         │ human PR review                ▲                     ▲
                                                         │ + all 5 CI checks green        │ gate exit 2         │ never marked
                                                         ▼  ── human only ──              │                     │   "Done"
                                                  ┌──────────────┐                  ┌──────────┐                │
                                                  │     Done     │                  │ Blocked  │◀───────────────┘
                                                  └──────────────┘                  └──────────┘
                                                  proven + evidence          unproven dep / failed integrity / OPA deny

  Re-entry: an amended requirement (REQ-22) moves a Done item back to Spec-Compiling; evidence flips proven → unproven.
```

**Two human-only edges** are deterministically enforced *upstream of Plane* and cannot be performed by any agent role:

- **`Spec-Verified → Plan-Approved`** — requires `plan-approved.json` whose `feature_list_sha` equals the SHA-256 of the current `feature_list.json`. The initializer does **not** write this; only the human does.
- **`Human-Review → Done`** — requires a human PR review plus all required CI checks green.

A third human-authored action: `* → HANDOFF` operator reconciliation and any `in_scope = false` flip. The durable store rejects an unattributed flip.

---

## 3. How to read the board

Each card is one **work item** = one agent run = one trip through the lifecycle above. The card's columns and badges decode as follows. These are the project's 10 custom fields (do not confuse them with labels):

| Field | Type | What it tells you |
|---|---|---|
| `agent_role` | dropdown | Who owns this run: `initializer · implementer · verifier · research · human` |
| `requirement_id` | text | The spec requirement it satisfies, e.g. `REQ-GATE-002` (pattern `^[A-Z]+-[A-Z]+-[0-9]{3}$`) |
| `evidence_status` | dropdown | `unproven · proven · failed` — the truth claim, set only by the verifier |
| `coverage_type` | dropdown | `functional · NFR · WIRING` |
| `run_state` | dropdown | `running · complete · handoff · blocked` |
| `worktree_branch` | text | The git branch for the slice (traceability) |
| `agent_run_id` | text | The LLM run id (the third leg of the traceability triple) |
| `ears_pattern` | dropdown | `ubiquitous · event-driven · state-driven · unwanted · optional · complex` |
| `gate` | dropdown | Which gate acted: `stop · pretooluse · posttooluse · subagentstop · opa · ci` |
| `output_hash` | text | `sha256:<64hex>` — content-addressed pointer to the Evidence_Record blob |

**Labels (22, six families)** are the fast visual filters layered on top:

- **Role:** `agent:initializer` · `agent:coder` · `agent:tester` · `agent:research` · `human:review`
- **Priority:** `priority:blocking` · `priority:high` · `priority:normal`
- **Type:** `type:functional` · `type:nfr` · `type:wiring`
- **Gate:** `gate:stop` · `gate:completion` · `gate:security`
- **Phase:** `phase:0` · `phase:1` · `phase:2` · `phase:3` · `phase:4`
- **Terminal:** `handoff` · `blocked` · `failed`

**Reading a card in three seconds:** *state* (where it is) → *`agent_role`* (who has it) → *`evidence_status`* (is it real yet). If `evidence_status = proven` the claim is backed by an `output_hash`; if `unproven`, the work is not yet trustworthy regardless of how far right the card sits.

---

## 4. The two orthogonal axes

The board is organized along two independent axes. Every work item has a position on **both** at once. This is the single most important idea for navigating ASCP: **Cycles answer *when*, Modules answer *what*.**

```
                         WHAT  (8 epic-Modules — capability)
                ┌───────────────────────────────────────────────────────────┐
                │ M1 Infra · M2 Governance · M3 Spec/Coverage · M4 Verify ·   │
   WHEN         │ M5 Completion-Gate · M6 Integration · M7 Observability ·    │
   (7 phase-    │ M8 Orchestration                                           │
    Cycles)     ├───────────────────────────────────────────────────────────┤
  C0 Spine      │                                                            │
  C1 Depth      │     one work item sits at exactly one (Cycle × Module)     │
  C2 Durability │     cell — its phase AND its epic                          │
  C3 Observ.    │                                                            │
  C4 Property   │                                                            │
  C5 Orchestr.  │                                                            │
  C6 Routing    │                                                            │
                └───────────────────────────────────────────────────────────┘
```

### Axis 1 — 7 phase-Cycles (WHEN): delivery sequence

Cycles are time-boxed delivery waves. They follow the roadmap (`ROADMAP.md`): a required spine, then phases that add depth, durability, observability, and a full property suite, then two optional phases.

| Cycle | Phase | What ships in it |
|---|---|---|
| **C0 — Spine** | Phase 0 | The minimum deterministic control loop: coverage model, Stop hook, Verifier subagent, git worktrees, one required CI check, Playwright behavioral proof |
| **C1 — Depth** | Phase 1 | Static analysis (CodeQL/SonarQube), OPA/Conftest policy, evidence-schema validation, PostToolUse hooks; sandboxed execution + secret scanning fold in here |
| **C2 — Durability** | Phase 2 | Postgres-backed coverage/evidence, PreCompact checkpoints, SLSA provenance; hash-chained audit-log integrity folds in here |
| **C3 — Observability** | Phase 3 | OpenTelemetry tracing + Langfuse, `requirement.id` propagation via W3C Baggage |
| **C4 — Property suite** | Phase 4 | The full property-based test suite (all 32 correctness properties) wired as a required CI gate |
| **C5 — Durable orchestration** | Phase 5 (optional) | Durable workflow execution + crash recovery (Temporal/Inngest) |
| **C6 — Predictive routing** | Phase 6 (optional) | Advisory next-step routing that never gates a decision |

Phases 0–6 are built, tested, and on `main` behind the required CI checks. Human handoff is a core terminal state from Phase 0 onward.

### Axis 2 — 8 epic-Modules (WHAT): capability area

Modules are the eight epics from the blueprint. They are stable groupings of capability; an item's Module does not change as it moves through Cycles. The board carries **49 stories** across these eight.

| Module | Epic | What it owns | Stories |
|---|---|---|---|
| **M1** | Core Plane Infrastructure & Self-Hosting | The self-hosted Plane substrate: 13 Docker services, durable storage, backup/restore, health checks | 8 |
| **M2** | Agentic Workspace & Governance Model | The 12-state workflow, 10 fields, 22 labels, role→permission/transition-authority matrix | 3 |
| **M3** | Intent → Spec Compilation & Coverage Model | EARS compilation, Z3 validation, proactive discovery, domain baselines, coverage model | 6 |
| **M4** | Verification Engine & Evidence | One-slice incremental execution, wiring verification, the 5-layer verifier, Evidence_Records | 4 |
| **M5** | Completion & Quality-Gate Automation | The fail-closed completion gate, supply-chain/security gates, eval-gating, DAST, kill-switch | 5 |
| **M6** | Agent Integration Layer — Plane ⇄ Agent | Inbound webhooks (HMAC), agent-run dispatch, REST write-back, the state-mirror | 7 |
| **M7** | Observability, Audit & Traceability | Bidirectional traceability, session continuity/durable state, OTel, hash-chained audit log | 6 |
| **M8** | Orchestration, Anti-Loopmaxxing & Human-in-the-Loop | Mid-flight steering, anti-loop controls, HANDOFF semantics, HITL approval, omission declaration | 10 |

**Why two axes matter:** "show me everything in Cycle C0" tells a sprint lead what is in flight *now*; "show me everything in Module M4" tells a verification owner the *whole* verification capability across all phases. Neither view is reachable from the other — that is why both exist.

---

## 5. The 7 curated Views

Views are saved filter/group/layout presets. Use them instead of building ad-hoc filters; each answers one recurring question. Open them from the project sidebar (Views).

| View | Layout | Groups / filters | What it shows | When to use it |
|---|---|---|---|---|
| **Pipeline** | Board (Kanban) | Columns = the 12 states, left→right | The whole lifecycle at a glance — every item in its current state | The default daily view; "where is everything right now" |
| **By-Epic** | Board | Group by **Module** (M1–M8) | Work organized by capability area, ignoring phase | A capability owner asking "what is the state of the whole verification/observability/etc. area" |
| **By-Agent-Role** | Board | Group by `agent_role` | What each role (`initializer · implementer · verifier · research · human`) currently owns | Load-balancing across the fleet; spotting a role with a pile-up |
| **By-Phase** | Board | Group by **Cycle** (C0–C6) / `phase:*` label | Work organized by delivery wave | Roadmap / release planning; "what is left in Spine vs Durability" |
| **Blocked & HANDOFF** | List | Filter state ∈ {`Blocked`, `HANDOFF`} (also `Failed`); sort by priority | The exception queue — everything a gate stopped or handed to a human | Triage first thing each session; clear this before starting new work |
| **Evidence-Pending** | List | Filter `evidence_status = unproven` AND state ∈ {`Agent-Executing`, `In-Verification`} | Items that have been worked but are **not yet proven** | The verifier's worklist; "what still needs an Evidence_Record before it can advance" |
| **Current-Sprint** | Board | Filter to the **active Cycle** | The in-flight phase only, in Kanban form | The sprint board for the team executing the current Cycle |

> **Reading priority:** start each session at **Blocked & HANDOFF** (clear exceptions), then **Evidence-Pending** (close out proof), then **Current-Sprint** (advance new work). The other four views are for planning and reporting.

---

## 6. The traceability model: requirement → story → task → subtask → Evidence_Record

ASCP's defining property is that everything is traceable end-to-end. The board is structured so you can walk from a single spec requirement down to the exact evidence blob that proves it, and back.

```
  requirement_id  (REQ-GATE-002)              ← the spec obligation (from .kiro requirements.md)
        │
        ▼
  Story / Work item  (one Plane issue)        ← carries EARS lines + acceptance criteria;
        │                                        lives in one Module, one Cycle; has an agent_role
        ▼
  Task  (category: Infrastructure │ API │ Orchestration)   ← a unit of build work on the issue
        │
        ▼
  Subtask  (checklist step)                   ← the concrete actions that complete a task
        │
        ▼
  Evidence_Record  (output_hash → sha256 blob)   ← captured by the verifier; the proof.
                                                   evidence_status flips unproven → proven only here.
```

Each level is materially anchored:

- **Requirement** — a `requirement_id` from `.kiro/specs/spec-to-evidence-control/requirements.md` (32 EARS requirements). Stamped on the work item's `requirement_id` field.
- **Story / work item** — one Plane issue carrying the EARS lines and acceptance criteria for that requirement. 49 stories cover the eight Modules.
- **Task** — each story decomposes into tasks tagged `Infrastructure`, `API (Plane Webhooks/REST)`, or `Orchestration`. These mirror `tasks.md`.
- **Subtask** — the checklist steps under a task; the literal actions a run performs.
- **Evidence_Record** — the load-bearing artifact. The verifier captures it, stores the blob content-addressed by `output_hash` (`sha256:<64hex>`), and links it to the `requirement_id` and commit SHA. Only then does `evidence_status` become `proven`.

**The traceability triple** binds the run to the code: `issue ↔ worktree_branch ↔ agent_run_id`. When an agent run produces a slice, all three are written onto the work item, so any proven item's full provenance — which issue, which git branch, which LLM run, which commit, which evidence hash — is reconstructable from the board alone. Drift between the board and Postgres always resolves *toward Postgres*; a manual Plane edit that the durable store does not support (e.g. dragging an `unproven` item to `Done`) is reverted and logged.

---

## 7. Working conventions (WIP & compaction)

**One slice at a time (single-WIP per run).** When an item enters **Agent-Executing**, the system drives exactly *one* inner loop: one slice, one `implementer` subagent, one isolated git worktree, one atomic commit. The implementer **never self-verifies** — verification is a separate `verifier` run. A scope-sequencing gate refuses to start a new slice while any prior in-scope item is still `unproven`. Practically: do not expect to see a single agent holding many `Agent-Executing` items; the model is one-in-flight, proven, then the next.

**Coverage is fail-closed.** The Stop gate refuses completion while any in-scope item is `unproven`. An item cannot reach **Done** on a self-report; it reaches Done only as the projection of a real Stop + OPA + CI pass.

**Compaction is checkpointed, not lossy.** When an agent's context is about to be compacted, the PreCompact hook checkpoints progress, evidence state, and `feature_list.json` to git and writes a durable `run_state.resume_state_hash`. On the next session the SessionStart hook reloads that state, recomputes the hash, and re-orients the agent to the exact item it was on. Durable run state lives outside model context — in files, git history, and Postgres — so a board item's position survives both context limits and crashes.

**HANDOFF is terminal, not a pause.** Cap, budget, or no-progress drives an item to **HANDOFF** with `run_state = handoff`. It is never silently retried into Done; a human picks it up.

---

## 8. The five gates behind "Done"

A work item reaching **Done** is backed by five required, non-bypassable status checks on `main` (the GitHub ruleset). The board mirrors their verdict via the `gate` field and `evidence_status`; it does not replace them.

| Required check (CI context) | Workflow | What it enforces |
|---|---|---|
| `Z3 formal-verification harness (34/34)` | `ci.yml` | The machine-checked completion / HANDOFF / exit-code invariants must hold |
| `Property + spine test suite` | `ci.yml` | The Hypothesis property suite + spine unit tests (Properties 1–32) |
| `Zero-evidence coverage gate (block merge on un-proven coverage)` | `coverage-gate.yml` | No merge while any in-scope item is `unproven` |
| `gitleaks secrets diff-scan (block merge on detected secret)` | `secrets-scan.yml` | A secret in the diff blocks the merge |
| `zap-baseline` | `zap-baseline.yml` | OWASP ZAP baseline DAST passes |

On a gate block (exit 2 / OPA deny / failed check) the item goes to **Blocked** with the `gate` field set. On a clean pass plus the human PR review, it advances `Human-Review → Done` with `evidence_status = proven`.

---

## 9. Quick reference

- **I'm new — where do I start?** The **ASCP — Start Here** page, then the **Pipeline** view.
- **What's stuck?** The **Blocked & HANDOFF** view.
- **What still needs proof?** The **Evidence-Pending** view.
- **Is this item real?** Check `evidence_status` — `proven` (with an `output_hash`) or not.
- **Who owns this?** The `agent_role` field / role label.
- **When is it shipping?** Its Cycle (C0–C6) / `phase:*` label.
- **What capability is it?** Its Module (M1–M8).
- **Why can't I drag this to Done?** Because Plane mirrors the gates — Done is granted only by a Stop + OPA + CI pass plus human PR review, and an unsupported edit is reverted.

---

*Grounded in `.kiro/specs/spec-to-evidence-control`, `docs/plane/PLANE_BLUEPRINT.md`, `docs/plane/plane_backlog.json`, `docs/github-ruleset.md`, `ROADMAP.md`, and the live Plane instance at `http://localhost:8090` (workspace `ascp`, project `ASCP`).*
