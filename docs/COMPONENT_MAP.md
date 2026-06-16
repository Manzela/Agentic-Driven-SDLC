# Component Map — The Spec-to-Evidence Traceability Matrix

**The single-source traceability artifact: requirement → component → property/CHECK → test → Plane board.**

This document maps **every built component** of the Agentic-Driven SDLC platform to the requirement it implements, the correctness property or CHECK constraint it satisfies, the test file that proves it, the delivery phase it ships in, and the Plane epic/module that tracks it. It is derived directly from the live repository — every row was read from the actual file, not inferred.

The system is an **autonomous Spec-to-Evidence SDLC control plane** running on the Claude Code substrate: it converts product intent into traceable, machine-verifiable software, using four subagents (initializer / implementer / verifier / research) as memory, verifier, scope-enforcer and auditor, and a **fail-closed completion gate** (Stop hook + OPA/Conftest + GitHub required status checks) that makes "done" impossible while any in-scope requirement is `unproven`. A self-hosted **Plane** PM control plane mirrors the same lifecycle for humans.

---

## At a glance

| Dimension | Count | Source of truth |
|---|---|---|
| Built components mapped here | **48** | 26 `tools/*.py` + 6 `.claude/hooks/*.py` + 4 `.claude/agents/*.md` + 8 `db/migrations/*.sql` + 4 `.github/workflows/*.yml` |
| EARS requirements | **32** | `.kiro/specs/spec-to-evidence-control/requirements.md` (Requirements 1–32) |
| Correctness properties | **32** | Properties 1–32 (design.md / tasks.md) |
| Z3 machine-checked assertions | **34** | `verification/formal_verification_merged.py` (14 core + 12 Kiro + 8 new) |
| Postgres tables | **8** | `db/migrations/001…008` |
| Build tasks | **57** | `.kiro/specs/spec-to-evidence-control/tasks.md` |
| Test files | **33** | 30 `tests/spine` + 2 `tests/property` + 1 `tests/integration` |
| Delivery phases | **0–6** | 5 required (0–4) + 2 optional (5–6) |
| Plane epics / modules | **E1–E8** | `docs/plane/PLANE_BLUEPRINT.md` · `docs/plane/plane_backlog.json` |
| Live required CI checks on `main` | **5** | `docs/github-ruleset.md` |

> **A note on the "REQ-*" namespace.** Two ID forms coexist. The canonical `feature_list.json` `CoverageItem.id` form is the three-segment `REQ-<DOMAIN>-NNN` (e.g. `REQ-VERIFY-007`), matched by `tools/req_id_scan.py` (`[A-Z]+-[A-Z]+-[0-9]{3}`). The spec also numbers its 32 EARS requirements `Requirement 1…32`, each carrying a **PRD reference** range of `REQ-*` IDs (e.g. Requirement 9 ⇒ `REQ-VERIFY-001..006`). This matrix cites both: the bold `Req N` is the EARS requirement, and the `REQ-*` codes are its PRD references as they appear in the component docstrings and `requirements.md`.

---

## How to read a row

Each component row carries six load-bearing columns:

- **Purpose** — what the component does, in one line, from its own docstring/header.
- **Requirement(s)** — the EARS `Requirement N` + `REQ-*` PRD references it implements (from the code citations cross-checked against `requirements.md`).
- **Property / CHECK** — the correctness Property number and/or Z3 `CHECK-*` assertion, or DB `CHECK` constraint, it satisfies. `—` means *verified at runtime/CI with no Z3 oracle* (documented intent, not a gap).
- **Test file(s)** — the test(s) that exercise it.
- **Phase** — the delivery phase (0–6) per the design.md Component Inventory.
- **Epic** — the Plane epic/module (E1–E8) that tracks the requirement.

---

## 1. Coverage / completion core (`tools/`)

The deterministic heart of the control plane: the rules every hook and CI gate single-source from, plus the four-field Evidence_Record contract and the merge gate.

| Component | Purpose | Requirement(s) | Property / CHECK | Test file(s) | Phase | Epic |
|---|---|---|---|---|---|---|
| `tools/coverage.py` | Canonical coverage-model helpers — `ALLOWED_TRANSITIONS`, field authority (status verifier-only, `in_scope` human-only), `has_unproven_in_scope`/`is_complete` completion query. Single-sourced by hooks + OPA gate. | **Req 5** (REQ-COV-001..006), **Req 10** (REQ-GATE-001) | Property 3 (status-transition edges); CHECK-1/CHECK-3 (completion from facts) | `test_control_plane_completion.py`, `test_invariants.py`, `test_spine_e2e.py` | 0 | E3 / E5 |
| `tools/evidence_collector.py` | Evidence_Record builder + validator: enforces the exactly-four-field contract (`test_file`, `test_name`, `output_hash` as `sha256:<64hex>`, `collected_at`) before any flip to `proven`. Imported by SubagentStop + PreToolUse status guard. | **Req 5** (5.3, 5.6), **Req 8** (8.3), **Req 9** (9.3), **Req 25** (25.1, 25.2) | Property 2 (four-field proven-transition gate); CHECK-7a/7c (missing `output_hash`/zero fields → UNSAT) | `test_evidence_collector.py` | 0 | E4 |
| `tools/feature_list_init.py` | `feature_list.json` initializer — builds a schema-valid empty coverage model (all items `unproven`, `in_scope=true`), writes atomically. The one seed write exempt from the PreToolUse guards. | **Req 5** (5.1) | — (schema-valid envelope; `feature_list.schema.json` draft-07) | `test_feature_list_init.py`, `test_feature_list_schema.py` | 0 | E3 |
| `tools/model_fingerprint.py` | Stable fingerprint of the coverage **model** (item set/types/priorities/deps/acceptance/scope, excluding mutable `status`/`evidence`). Binds plan-approval to the model shape so a `proven`-flip is not coverage drift. | **Req 18** (18.4, the `feature_list_sha` SHA-binding) | Property 6 (plan-approval SHA-binding) | `test_model_fingerprint.py` | 0 | E2 / E3 |
| `tools/materialize_feature_list.py` | Compiles the website spec (`docs/website/autonomous-agent.dev`, 205 EARS reqs) into the **209-item** `apps/web/feature_list.json` coverage model (205 reqs + 4 supply-chain/Bucket-A items), all `unproven`. | **Req 1** (REQ-SPEC-001..004), **Req 5** (5.1) | — (schema-valid against `feature_list.schema.json`) | `test_materialize.py` | 0 | E3 |
| `tools/coverage_gate.py` | OPA-equivalent zero-evidence **merge** gate (Python twin of `coverage_query.rego`): denies merge if any in-scope item is not `proven`-with-complete-evidence; empty model denies; **fails closed**. | **Req 5** (5.7), **Req 10** (10.3) — REQ-GATE-002/003 | Property 22 (OPA zero-evidence at merge) | `test_coverage_gate.py` | 1 | E5 |
| `tools/opa_input.py` | Builds the `{unproven_in_scope, missing_evidence}` Conftest/OPA input document from the coverage model that the Rego policy evaluates. | **Req 10** (REQ-GATE-002/003) | Property 22 (input to the OPA zero-evidence policy) | `test_control_plane_completion.py` | 1 | E5 |
| `tools/prove_trivial_slice.py` | End-to-end demonstrator: drives a trivial slice through the **real** spine — captures live HTML, builds a four-field Evidence_Record over real bytes, runs it through the SubagentStop gate (re-derives hash, rejects same-session), flips to `proven`, confirms Stop reports `COMPLETE`. | **Req 9** (9.2/9.3), **Req 10** (10.1) | Property 24 (evidence provenance / independent verification) | `test_control_plane_completion.py` | 0 | E4 |

---

## 2. Spec compilation & discovery (`tools/`)

Turns terse intent into an EARS-validated, gap-free spec — bounded so it cannot loop forever or self-declare done.

| Component | Purpose | Requirement(s) | Property / CHECK | Test file(s) | Phase | Epic |
|---|---|---|---|---|---|---|
| `tools/spec_validator.py` | Non-LLM EARS validator returning `{contradictions, ambiguities, uncovered, violation_count}`. Structural checks: single `ears_pattern` (5-enum), vague-adjective scan, completeness, consistency. The authoring agent has no vote. | **Req 1** (1.2, 1.4), **Req 4** (4.1) — REQ-SPEC-001..004/020..024 | Property 14 (validator return contract), Property 16 (EARS-pattern uniqueness), Property 17 (vague-adjective scan) | `test_spec_validator.py` | 0 | E3 |

---

## 3. Traceability & orphan detection (`tools/`)

Every requirement linked forward to verification, every code unit linked back to a requirement.

| Component | Purpose | Requirement(s) | Property / CHECK | Test file(s) | Phase | Epic |
|---|---|---|---|---|---|---|
| `tools/req_id_scan.py` | Single source of truth for requirement-ID extraction (`[A-Z]+-[A-Z]+-[0-9]{3}`). Imported by **both** `orphan_detector.py` and `traceability_writer.py` so the regex cannot drift. | **Req 6** (6.2, 6.3) | Properties 10 + 11 (shared ID-pattern dependency) | (covered via `test_orphan_detector.py`, `test_traceability_writer.py`) | 1 | E7 |
| `tools/traceability_writer.py` | Commit-trailer parser + the **commit-has-req-id** gate (`assert_commit_has_req_id`); builds the `req → code → test` rows of the durable `traceability_links` graph. | **Req 6** (6.1, 6.2) — REQ-TRACE-001..003 | Property 10 (commit-trailer requirement ID) | `test_traceability_writer.py` | 2 | E7 |
| `tools/orphan_detector.py` | Bidirectional orphan check — forward (code with no req ref) **and** backward (req with no verification); either non-empty list blocks the run. CI `traceability-gate` caller. | **Req 6** (6.3) | Property 11 (bidirectional orphan detection; no Z3 by design) | `test_orphan_detector.py` | 1 | E7 |

---

## 4. Verification engine — fifth layer & quality (`tools/`)

The independent Verifier's structural / semantic / behavioral / security / **perf-a11y** layers, plus the LLM-output quality gate.

| Component | Purpose | Requirement(s) | Property / CHECK | Test file(s) | Phase | Epic |
|---|---|---|---|---|---|---|
| `tools/wiring_checker.py` | Static call-graph / dead-code analysis (AST). Whole-repo reachability from seeded entry points; emits `type:"WIRING"` coverage-item candidates. The structural-layer AST engine the PostToolUse hook invokes. Never gates. | **Req 8** (REQ-EXEC-010..012), **Req 9** (9.1 structural AST) | Property 1 (WIRING emission) | `test_wiring_checker.py` | 1 | E4 |
| `tools/perf_a11y_verifier.py` | The Verifier's **fifth layer** — dispatches on `subtype`: `performance` (k6/Lighthouse vs numeric budgets), `accessibility` (axe-core, zero WCAG-A/AA), `ui-screen` (every declared screen/state has a behavioral render Evidence_Record). Pure assertion; reads budgets, owns none. | **Req 25** (25.1, 25.2, 25.3) — REQ-VERIFY-007/008 | Property 31 (perf/a11y/ui-screen evidence required; PBT, no Z3) | `test_perf_a11y_verifier.py` | 1 | E4 |
| `tools/deepeval_gate.py` | DeepEval pytest-native eval gate — `evaluate_gate` (pure threshold core) + `assert_gate` (`deepeval.assert_test()` wrapper). Gates LLM output quality at faithfulness ≥ 0.8 / answer-relevancy ≥ 0.7. REQUIRED CI check `deepeval-gate`. A deterministic quality gate, **not** the completion gate. | **Req 30** (REQ-EVAL-001) | — (no Z3/Property; named CI tool is its verification per requirements.md:542) | `test_deepeval_gate.py` | 3 | E5 |

---

## 5. Durable store, state integrity & audit log (`tools/`)

The single durable substrate (8 tables), resumed-state integrity, and the tamper-evident hash-chained gate-decision log.

| Component | Purpose | Requirement(s) | Property / CHECK | Test file(s) | Phase | Epic |
|---|---|---|---|---|---|---|
| `tools/store.py` | Durable-store abstraction over the 8 migration tables. Reference backend = stdlib `sqlite3` (faithful translation of the Postgres DDL incl. all `CHECK` constraints); Postgres adapter seam optional. `store_evidence` mirrors the four-field proven-transition gate (raises `EvidenceIncompleteError`). | **Req 16** (16.1, 16.2, 16.3) — REQ-STORE-001..003 | Property 19 (evidence round-trip), Property 2 (four-field gate), Property 24 (provenance) | `test_store.py` | 2 | E7 |
| `tools/state_integrity.py` | Recomputes the resumed-state hash on SessionStart (`sha256` over the canonical in-scope `feature_list.json` projection + named `run_state` fields); writes the **non-blocking** `resume_integrity_ok` verdict. The exit-2 block is the separate PreToolUse integrity guard. | **Req 23** (REQ-STATE-005) | Property 26 (resumed-state integrity; impl/wiring PBT). Logic abstraction: CHECK-11a/11b | `test_state_integrity.py` | 2 | E7 |
| `tools/audit_log.py` | Tamper-evident gate-decision audit-log **PRODUCER**: `append(event, tool, decision, reason, requirement_id, actor_agent)`. Hash chain `entry_hash = sha256(canonical_row ‖ prev_hash)`. Called by Stop / PreToolUse / SubagentStop on every allow/block. | **Req 27** (27.1, 27.4, 27.5) — REQ-AUDIT-001 | Property 28 (audit-log tamper detection; runtime/CI, no Z3) | `test_audit_log.py` | 2 | E7 |
| `tools/audit_verify.py` | Hash-chain **VERIFIER** — re-walks `gate_audit_log` rows, recomputes each `entry_hash` and checks `prev_hash` linkage; imports the **shared** canonicalizer from `audit_log`. On-demand + merge-time CI required check. Fails closed on an unreadable chain. | **Req 27** (27.2, 27.6) — REQ-AUDIT-002/003 | Property 28 (audit-log tamper detection) | `test_audit_verify.py` | 3 | E7 |
| `tools/actor_identity.py` | Resolves the acting agent identity from **runtime** signals only (`CLAUDE_AGENT_NAME` env + hook `session_id`), never from the tool payload. Imported by SubagentStop + PreToolUse so a forged `actor_agent` cannot promote a self-graded flip. | **Req 9** (9.2 independence), **Req 5** (5.2 status authority) | Property 24 (evidence provenance / actor independence) | `test_actor_identity.py`, `test_actor_separation.py` | 0 | E4 |

---

## 6. Security, sandbox & kill-switch (`tools/`)

Supply-chain isolation and the operator's near-real-time capability kill-switch.

| Component | Purpose | Requirement(s) | Property / CHECK | Test file(s) | Phase | Epic |
|---|---|---|---|---|---|---|
| `tools/sandbox_guard.py` | Sandbox / worktree-isolation predicates: `egress_allowed` (network DENIED by default), `check_worktree_confinement` (FS writes confined to the per-slice worktree; blocks `../`, absolute-outside, symlink escape). Default-deny / fail-closed. | **Req 17** (17.4) | Property 20-family (sandbox isolation; REQ-GATE-005 fail-closed) | `test_sandbox_guard.py` | 1 | E5 |
| `tools/kill_switch.py` | OpenFeature/flagd kill-switch client: a capability is ENABLED iff `kill.all` off **and** its `kill.<capability>` off; unreachable flagd → DISABLED (fail-closed). Queried at start-of-turn by each agent entry point. | **Req 32** (32.1, 32.2, 32.3) — REQ-CTRL-001 | — (REQ-GATE-005 fail-closed; runtime/CI verified) | `test_kill_switch.py` | 2 | E5 |

---

## 7. Observability & predictive routing (`tools/`)

Requirement-tagged tracing, reasoning-loop detection, and the off-gate predictive accelerator.

| Component | Purpose | Requirement(s) | Property / CHECK | Test file(s) | Phase | Epic |
|---|---|---|---|---|---|---|
| `tools/observability.py` | OTel-shaped span primitives (pure stdlib, SDK optional): `build_span` (model/tool/subagent spans + `requirement.id` W3C Baggage), `forward_hook_decision` (gate-making hooks only), `detect_reasoning_loop` (K=3 identical tool-call signatures via `claude.span.kind="reasoning"` attribute). | **Req 12** (12.1, 12.3, 12.4), **Req 26** (REQ-OBS-006) | Property 12 (Baggage `requirement.id`), Property 21 (hook decision forwarding) | `test_observability.py` | 3 | E7 |
| `tools/predictive_router.py` | **Optional, off-gate** predictive next-step routing — advisory context only. `gate_decision_is_prediction_independent` is the runtime witness that the gate verdict is identical under any/no prediction. | **Req 19** (REQ-PRED-001..003) | Property 4; CHECK-5 (a differing prediction cannot change a gate decision → UNSAT) | `test_predictive_router.py` | 6 | E8 |

---

## 8. Durable orchestration — optional Phase 5 (`tools/`)

Pure-Python reference of the Temporal/Inngest durable outer loop; off the delivery-gating path.

| Component | Purpose | Requirement(s) | Property / CHECK | Test file(s) | Phase | Epic |
|---|---|---|---|---|---|---|
| `tools/durable_orchestrator.py` | Temporal/Inngest-style durable-execution reference: activity wrapper with bounded `RetryPolicy` → `Handoff` on exhaustion; event-sourced deterministic replay; content-addressed checkpoint/resume; durable timers. Decision path reads no wall-clock/random. | **Req 15** (15.2), **Req 14** (REQ-LOOP-001..003), **Req 21** (REQ-LOOP-005), **Req 11** (REQ-STATE-001..004) | Property 7-family (HANDOFF terminal state); CHECK-3 (cap/budget/no-progress → HANDOFF only) | `test_durable_orchestrator.py` | 5 | E8 |
| `tools/event_bus.py` | Inngest-style event-driven durable-step bus: append-only `emit`, handler `on`, memoized `run_step` (at-most-once), at-least-once `deliver` with per-delivery dedup. `snapshot`/`restore` for crash-resume. Off the gating path. | **Req 15** (15.1, 15.2) — REQ-ORCH-001..003 | — (Phase-5 reference semantics; runtime verified) | `test_event_bus.py` | 5 | E8 |

---

## 9. Claude Code hooks (`.claude/hooks/`)

The **sole deterministic mid-flight intervention layer**. Command-type hooks only (fail-closed); exit 2 = block, exit 1 = non-blocking feedback. Configured in `.claude/settings.json`.

| Component | Purpose | Requirement(s) | Property / CHECK | Test file(s) | Phase | Epic |
|---|---|---|---|---|---|---|
| `.claude/hooks/pre_tool_use_hook.py` | **The only true prevention gate** (exit 2 blocks before the write lands). Enforces: `status` writable only by verifier, `in_scope` only by a human-signed change, protected-artifact guard (tests/schema/CI/hooks), plan-approval + SHA-binding, scope sequencing, resumed-state integrity, secret-block. Identity from `actor_identity`. Fails closed. | **Req 5** (5.2), **Req 7** (7.4, 7.5), **Req 13** (13.2, 13.3), **Req 17** (17.5), **Req 18** (18.1, 18.4), **Req 23** (23.2) | Properties 3, 5, 6, 20; CHECK-4f (no write without approved plan), CHECK-6a (no new slice while prior unproven) | `test_pre_tool_use_authority.py` | 0 | E2 / E4 / E5 |
| `.claude/hooks/stop_hook.py` | Stop-gate `evaluate_stop` + `check_no_progress` watchdog. **Order is load-bearing**: HANDOFF triggers (cap/budget/no-progress) evaluated FIRST and ALLOW termination (exit 0); only then do blocking gates (`violation_count`, unproven in-scope) apply. The infinite-block fix. Fails closed. | **Req 4** (4.2), **Req 10** (10.2, 10.4), **Req 14** (REQ-LOOP-002), **Req 21** (REQ-LOOP-005), **Req 27** (audit producer) | Properties 7, 8; CHECK-1, CHECK-3, CHECK-8a/8b (no-progress → HANDOFF only) | `test_stop_hook.py`, `test_control_plane_completion.py` | 0 | E5 / E8 |
| `.claude/hooks/subagent_stop_hook.py` | Accepts a result only if independently honest: runtime-resolved `actor_agent` (fix #1), distinct verifier/implementer sessions (fix #2), re-derived `output_hash` (fix #3), four-field evidence, verifier-actor check, and the **omission-declaration guard** (non-null `omission_declaration`, exit 2). Fails closed. | **Req 9** (9.5), **Req 5** (5.6), **Req 29** (29.2, 29.3) — REQ-SPEC-018 | Property 2 (four-field), Property 24 (provenance), Property 30; CHECK-13a/13b (null omission → block) | `test_subagent_stop_actor.py` | 0 / 2 / 3 | E4 / E8 |
| `.claude/hooks/post_tool_use_hook.py` | Fires after Write/Edit/MultiEdit: runs lint + edit-time Semgrep + `wiring_checker` over changed files, surfaces findings as **next-turn feedback**. **Never blocks** (exit 1) — the write already landed. Deliberately **not** an audit-log producer. | **Req 9** (9.4), **Req 13** (13.2), **Req 8** (8.1 wiring trigger) — REQ-VERIFY-004 | Property 21 (PostToolUse never-blocks / exit-1 invariant) | `test_remaining_hooks.py` | 1 | E4 |
| `.claude/hooks/session_start_hook.py` | Loads git status + `claude-progress.txt` + `feature_list.json` and injects a structured summary (Phase-0). On resume, also computes the resumed-state hash via `state_integrity` and reports `resume_integrity_ok` (Phase-2 augmentation). **Non-blocking by contract** (exit 0). | **Req 11** (11.3) — REQ-STATE-003, **Req 23** (REQ-STATE-005, compute half) | Property 26 (resumed-state integrity, compute side) | `test_session_start_hook.py` | 0 | E7 |
| `.claude/hooks/pre_compact_hook.py` | Checkpoints the three durable-state artifacts (`claude-progress.txt`, evidence state, `feature_list.json`) to the **main** worktree before compaction. **Non-blocking** — a checkpoint is a pure write; not an audit-log producer; exits 0 even on failure. | **Req 11** (11.2) — REQ-STATE-002 | — (non-blocking checkpoint; unit+integration verified, no Z3) | `test_remaining_hooks.py` | 1 | E7 |

---

## 10. Subagent definitions (`.claude/agents/`)

The four bounded roles of the inner loop. Each carries an explicit permission scope; **none but the verifier** may write `tests/` or flip `status`, and the implementer never self-verifies.

| Component | Purpose | Requirement(s) | Property / CHECK | Test file(s) | Phase | Epic |
|---|---|---|---|---|---|---|
| `.claude/agents/initializer.md` | Spec Compiler + Coverage-Model Builder. Compiles intent → EARS-validated spec (via `spec_validator`), expands against the domain baseline, builds `feature_list.json` (all `unproven`), presents for human sign-off. Never writes `plan-approved.json`. Scope: spec artifacts + `feature_list.json` + baselines. | **Req 1**, **Req 2**, **Req 4** — REQ-SPEC-001..004/010..012/020..024 | Property 14/16/17 (delegates validation); Property 6 (presents for approval) | `test_spec_validator.py`, `test_pre_tool_use_authority.py` (scope) | 0 | E3 |
| `.claude/agents/implementer.md` | Coding subagent — exactly one highest-priority `unproven` slice per session in an isolated worktree, one atomic commit with the req-ID trailer. Returns **no Evidence_Record**; the Verifier is invoked separately. Scope: impl source in the assigned worktree only; NO `tests/`, schema, CI, other worktrees. | **Req 7** (7.1, 7.2, 7.3) — REQ-EXEC-001..005 | Property 24 (never self-verifies); CHECK-6a (one-slice discipline) | `test_pre_tool_use_authority.py`, `test_subagent_stop_actor.py` | 0 | E4 |
| `.claude/agents/verifier.md` | Independent evaluator — runs all five verification layers, captures Evidence_Records, flips `unproven → proven` only on all-pass + coverage ≥ 85%. The **only** actor permitted to write `tests/` and `status`. Read-only on `src/`; never self-verifies. | **Req 9** (9.1, 9.2, 9.6), **Req 25** (perf/a11y/ui) — REQ-VERIFY-001..008 | Property 24 (independence), Property 2 (evidence), Property 31 (fifth layer) | `test_subagent_stop_actor.py`, `test_perf_a11y_verifier.py`, `test_actor_separation.py` | 0 | E4 |
| `.claude/agents/research.md` | Domain-Baseline Checklist Sourcer — on a new product class, researches competitive analysis / standards / OSS refs and drafts `baselines/<class>.md`; every claim carries a source URL + authority-tier label and passes a fact-check before human review. Never uses a checklist until approved. Scope: `baselines/` + WebSearch/WebFetch. | **Req 3**, **Req 24** — REQ-SPEC-013..017 | Property 27 (DRAFT-checklist-not-used; CHECK-12a/12b), Property 29 (research epistemic integrity) | (covered via property suite — Property 27/29) | 0 | E3 / E8 |

---

## 11. Database migrations (`db/migrations/`)

The eight-table durable Postgres store — the single source of truth for coverage queries, reconstructable independently of any model session. Reference-mirrored in `tools/store.py`.

| Component | Table / purpose | Requirement(s) | Property / DB CHECK | Test file(s) | Phase | Epic |
|---|---|---|---|---|---|---|
| `001_requirements.sql` | `requirements` — authoritative spec record per run. `CHECK type ∈ {functional, NFR, WIRING}`; `nfr_subtype` enum. | **Req 16** (16.1), **Req 5** (5.1) | DB `CHECK` (type / nfr_subtype domains) | `test_migrations.py` | 2 | E7 |
| `002_coverage_items.sql` | `coverage_items` — mutable status view. `CHECK status ∈ {unproven, proven, failed}` default `unproven`; `subtype` enum; `in_scope BOOLEAN` default TRUE. | **Req 5** (5.1, 5.7, 5.8), **Req 16** | Property 3; DB `CHECK` (status / subtype / in_scope) | `test_migrations.py`, `test_store.py` | 2 | E7 |
| `003_traceability_links.sql` | `traceability_links` — bidirectional `requirement↔code↔test↔commit↔owner` graph. `CHECK link_type / direction`. | **Req 6** (6.1) — REQ-TRACE-001 | Property 10/11; DB `CHECK` (link_type / direction) | `test_migrations.py` | 2 | E7 |
| `004_evidence_records.sql` | `evidence_records` — the four Evidence fields + `output_hash` format `CHECK (^sha256:[a-f0-9]{64}$)` + `actor_agent` (provenance). | **Req 5** (5.3, 5.6), **Req 16** (16.2) | Property 2, Property 24; DB `CHECK` (output_hash format, evidence completeness) | `test_migrations.py`, `test_store.py` | 2 | E7 |
| `005_run_state.sql` | `run_state` — per-session execution state. `CHECK status` + `stop_hook_active`, `no_progress_n`, `resume_integrity_ok`, `violation_count`, `retry_count`, `resume_state_hash`. | **Req 10** (10.4), **Req 11** (11.1), **Req 14**, **Req 23** | Property 7/8/26; DB `CHECK` (status domain) | `test_migrations.py` | 2 | E7 |
| `006_domain_baseline_checklists.sql` | `domain_baseline_checklists` — product-class checklist version history (DRAFT/approved lifecycle). | **Req 3** (3.2, 3.3), **Req 24** (24.1) — REQ-SPEC-016 | Property 27 (checklist-approval-before-use) | `test_migrations.py` | 2 | E7 / E8 |
| `007_requirement_versions.sql` | `requirement_versions` — amendment history (prior/new text, author, timestamp, rationale); `ON DELETE RESTRICT`. | **Req 22** — REQ-COV-007 | Property 25; CHECK-10a/10b (amendment monotonicity) | `test_migrations.py` | 2 | E7 / E3 |
| `008_gate_audit_log.sql` | `gate_audit_log` — tamper-evident hash-chained log. `seq BIGSERIAL`, `prev_hash` + `entry_hash`, `CHECK decision ∈ {allow, block}`; append-only (REVOKE + trigger). | **Req 27** (27.1) — REQ-AUDIT-001/002 | Property 28; DB `CHECK` (decision domain) + append-only trigger | `test_migrations.py`, `test_audit_log.py`, `test_audit_verify.py` | 2 | E7 |

---

## 12. CI workflows (`.github/workflows/`)

The merge-boundary enforcement. The completion gate lives where the model cannot talk past it.

| Component | Purpose | Requirement(s) | Property / CHECK | Required on `main`? | Phase | Epic |
|---|---|---|---|---|---|---|
| `ci.yml` | Two jobs: **`formal-verification`** runs `verification/formal_verification_merged.py` (must exit 0, **34/34**); **`tests`** runs the Hypothesis property + spine test suite. | **Req 4**, **Req 10**, **Req 13**, **Req 14** (the Z3-checked invariants) | All 34 Z3 CHECKs; Properties 1–32 | ✅ (2 contexts) | 0–4 | E4 / E5 / E8 |
| `coverage-gate.yml` | Runs the Python OPA twin (`coverage_gate.deny_merge`) against `feature_list.json`; skips gracefully when absent (runtime artifact), load-bearing once present. Job id `coverage-gate`. | **Req 5** (5.7), **Req 10** (10.3) — REQ-GATE-002/003 | Property 22 (OPA zero-evidence at merge) | ✅ | 1 | E5 |
| `secrets-scan.yml` | gitleaks diff-scan — merge-side half of "block the commit or merge": a secret in the PR diff fails the `secrets-scan` check. (Commit-side half = the PreToolUse secret-block guard.) | **Req 17** (17.2) — REQ-SEC-002 | Property 32 (CI secrets diff-scan blocks merge) | ✅ | 1 | E5 |
| `zap-baseline.yml` | OWASP ZAP baseline passive DAST scan (`zaproxy/action-baseline@v0.12.0`, `fail_action: true`) against the app stood up at `http://localhost:8080`. Baseline only; active scan out of v1 scope. | **Req 31** (REQ-SEC-008) | — (CI-gate obligation, deliberately no Z3/Property) | ✅ | 2 | E5 |

> **Live required checks (5).** Per `docs/github-ruleset.md`, the enforced contexts on `main` are: `Z3 formal-verification harness (34/34)`, `Property + spine test suite` (both from `ci.yml`), `Zero-evidence coverage gate`, `gitleaks secrets diff-scan`, and `zap-baseline`. The canonical fuller list in `tasks.md` additionally enumerates `audit-chain-verify`, `traceability-gate`, and `deepeval-gate` as registerable required checks; those workflows/gates exist (`audit_verify.py`, `orphan_detector.py`, `deepeval_gate.py`) and become load-bearing when registered.

---

## Phase → Cycle map

The seven delivery phases (0–6) are the platform's build waves; on the live Plane board each is opened as a **cycle** (`cycle.created` ⇒ a control-plane phase boundary; board labels `phase:0`…`phase:4` for the five required phases). Phases 0–4 are required and built; 5–6 are optional and present as reference implementations.

| Phase | Cycle (Plane) | Theme | Status | Representative components |
|---|---|---|---|---|
| **0** | `Phase 0 — Spine` | Minimum viable spine: coverage model + Stop hook + independent verifier + worktrees + required check + Playwright proof | Built | `stop_hook.py`, `pre_tool_use_hook.py`, `session_start_hook.py`, `subagent_stop_hook.py`, `spec_validator.py`, `evidence_collector.py`, `coverage.py`, the 4 agents |
| **1** | `Phase 1 — Verification Depth` | Semgrep + OPA/Conftest + PostToolUse + schema validation + wiring/orphan + perf-a11y | Built | `wiring_checker.py`, `orphan_detector.py`, `coverage_gate.py`, `opa_input.py`, `perf_a11y_verifier.py`, `post_tool_use_hook.py`, `pre_compact_hook.py`, `sandbox_guard.py`, `secrets-scan.yml` |
| **2** | `Phase 2 — Durable State` | Postgres 8-table store + SLSA + resumed-state integrity + audit-log producer + kill-switch + DAST | Built | `db/migrations/001…008`, `store.py`, `state_integrity.py`, `audit_log.py`, `traceability_writer.py`, `kill_switch.py`, `zap-baseline.yml` |
| **3** | `Phase 3 — Observability` | OTel + Langfuse + `requirement.id` Baggage + hook-decision forwarding + reasoning-loop detection + audit verify + eval gate | Built | `observability.py`, `audit_verify.py`, `deepeval_gate.py` |
| **4** | `Phase 4 — Property-Based Tests` | Full Hypothesis PBT suite — all correctness properties as required CI | Built | `tests/property/*`, `formal_verification_merged.py` (the 34/34 harness) |
| **5** | `Phase 5 — Durable Orchestration (optional)` | Temporal/Inngest durable outer loop, off the gating path | Built (reference) | `durable_orchestrator.py`, `event_bus.py` |
| **6** | `Phase 6 — Predictive Routing (optional)` | Read-only predictive next-step routing, off the gate | Built (reference) | `predictive_router.py` |

---

## Epic → Module map (Plane board)

Eight Plane epics/modules (E1–E8) track the platform. **E1** and **E6** carry the `REQ-INFRA-*` / `REQ-INT-*` namespaces (the Plane self-hosting substrate and the Plane⇄agent integration layer); **E2–E5, E7, E8** map directly to the 32 canonical `.kiro` EARS requirements. Source: `docs/plane/PLANE_BLUEPRINT.md` + `docs/plane/plane_backlog.json` (8 epics, 49 stories).

| Epic | Module title | Canonical requirements mapped | Primary components |
|---|---|---|---|
| **E1** | Core Plane Infrastructure & Self-Hosting | `REQ-INFRA-001..008` (substrate; cross-refs Req 12, Req 16) | Plane Docker stack (10 services + 4 stores + Caddy proxy, host port 8090) — infrastructure, not platform code |
| **E2** | Agentic Workspace & Governance Model | **Req 15** (Orchestration), **Req 18** (HITL Approval), **Req 28** (Capability-Role Taxonomy) | `pre_tool_use_hook.py` (plan-approval), `model_fingerprint.py`, the 4 agent role definitions |
| **E3** | Intent→Spec Compilation & Coverage Model | **Req 1, 2, 3, 4, 5, 22** | `spec_validator.py`, `feature_list_init.py`, `materialize_feature_list.py`, `coverage.py`, `initializer.md`, `research.md`, `007_requirement_versions.sql` |
| **E4** | Verification Engine & Evidence | **Req 7, 8, 9, 25** | `evidence_collector.py`, `wiring_checker.py`, `perf_a11y_verifier.py`, `actor_identity.py`, `prove_trivial_slice.py`, `subagent_stop_hook.py`, `post_tool_use_hook.py`, `implementer.md`, `verifier.md` |
| **E5** | Completion & Quality-Gate Automation | **Req 10, 17, 30, 31, 32** | `stop_hook.py`, `coverage_gate.py`, `opa_input.py`, `deepeval_gate.py`, `sandbox_guard.py`, `kill_switch.py`, `coverage-gate.yml`, `secrets-scan.yml`, `zap-baseline.yml` |
| **E6** | Agent Integration Layer — Plane ⇄ Agent | `REQ-INT-001..007` (webhook ingest, run dispatch, REST write-back, provisioning, mirror, integration OTel, anti-Plane-gating) | Plane ingress receiver + REST write-back (integration layer; cross-refs Req 6, 12) |
| **E7** | Observability, Audit & Traceability | **Req 6, 11, 12, 16, 23, 27** | `observability.py`, `store.py`, `state_integrity.py`, `audit_log.py`, `audit_verify.py`, `traceability_writer.py`, `orphan_detector.py`, `req_id_scan.py`, `session_start_hook.py`, `pre_compact_hook.py`, `db/migrations/*` |
| **E8** | Orchestration, Anti-Loopmaxxing & HITL | **Req 13, 14, 15, 18, 19, 20, 21, 24, 26, 29** | `durable_orchestrator.py`, `event_bus.py`, `predictive_router.py`, `stop_hook.py` (HANDOFF/no-progress), `subagent_stop_hook.py` (omission guard), `observability.py` (reasoning-loop) |

---

## Coverage completeness

Every one of the 48 built components appears in exactly one component table above; every component carries a requirement, a property/CHECK (or an explicit `—` for documented runtime/CI verification), a test file, a phase, and an epic. The traceability graph is closed in both directions:

- **Forward** — every EARS requirement (Req 1–32) maps to ≥1 component and ≥1 epic (Appendix table in `requirements.md`, zero `UNMAPPED`).
- **Backward** — every component references ≥1 requirement (the orphan-detector contract, Property 11, blocks any that does not).

The matrix is the load-bearing artifact behind the platform's central claim: **"done" is a machine fact — requirement → component → property → test → board — not a self-report.**

---

*Generated from the live repository at `/Users/danielmanzela/ascp-platform-phases`. Counts verified against the actual files: 26 `tools/*.py`, 6 hooks, 4 agents, 8 migrations, 4 workflows (48 components); 33 test files; 32 EARS requirements; 32 correctness properties; 34 Z3 assertions; 8 tables; 57 tasks; 8 epics; 5 live required CI checks.*
