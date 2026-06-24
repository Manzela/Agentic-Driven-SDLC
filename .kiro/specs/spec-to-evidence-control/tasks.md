# Implementation Plan: Spec-to-Evidence Coverage Control System

## Overview

Build the autonomous agentic software-delivery control plane on the Claude Code substrate in five required phases (0–4) plus two optional phases (5–6): Phase 5 = optional Temporal/Inngest durable execution, Phase 6 = optional predictive routing. Phase 0 (spine) is the hard prerequisite for all subsequent phases: every spine component must be coded, wired, and smoke-tested before any Phase 1 task begins. Implementation language is Python throughout.

---

## Tasks

### Phase 0 — Spine

- [ ] 1. Repo scaffold and Python environment
  - Create directory tree: `.claude/hooks/`, `.claude/agents/`, `tools/`, `schema/`, `tests/unit/`, `tests/integration/`, `tests/property/`, `tests/smoke/`, `db/migrations/`, `.github/workflows/`, `.github/policies/`, `baselines/`
  - Create `pyproject.toml` (or `requirements.txt`) pinning `z3-solver`, `hypothesis`, `jsonschema`, `psycopg2-binary`, `semgrep`, `playwright`, `deepeval`, and the perf/a11y tool dependencies `k6`, `lighthouse` (Lighthouse CLI / lighthouse-ci), and `@axe-core/playwright` (or `playwright-axe`) *(Reconciliation 2026-06-16: added `deepeval` (imported by `tools/deepeval_gate.py`, task 55) and the `k6` / Lighthouse / axe-core perf/a11y tools (consumed by the `perf_a11y_verifier` capability, task 51) — these were previously imported/consumed by build tasks but never declared/pinned here.)*
  - Create `.claude/settings.json` (or `.kiro/settings.json`) stub for hook wiring (populated in task 9) *(Reconciliation 2026-06-16: was `.vscode/settings.json` "populated in task 8" — `.vscode/` is gitignored (.gitignore) so a hook binding there would never commit/load (silent fail-open), and task 8 is `subagent_stop_hook.py`; PreCompact and all hooks are registered by task 9.1. Canonical path is `.claude/settings.json` per design hook-wiring table; PreCompact command binding `python3 .claude/hooks/pre_compact_hook.py`.)*
  - Create `claude-progress.txt` placeholder and `.gitignore` entries
  - Create the repo-root `CLAUDE.md` durable-invariant anchor (A9) — the CH-11 single home for session-invariant doctrine that the steering reason strings (PreToolUse / SubagentStop) and the goal directive reference **by short name** instead of restating per fire. It MUST carry: (1) the four durable invariants — actor-independence (the `verifier.md`-byte-consistent verifier-only-flips rule), human-owned artifacts (only a human writes `plan-approved.json` / flips `in_scope`), the canonical-source pin (`feature_list.json` is the one coverage source), and verifier-only Evidence_Record production; (2) the four named charter doctrines — CH-01 (steer to the next action, never a bare verdict / single canonical source), CH-10 (vary/escalate on repeat, bounded 2–3 rungs → HANDOFF, i.e. escalate-don't-re-inject), plus the predictions-never-gate and locate-the-oracle-before-any-done-claim doctrines; (3) the four forensics-fix P2 doctrines — A-LOOP-01 (define a checkable end-state before any teardown/disable done-claim), B-AMBIG-01 (hedge on named targets), B-OVERSPEC-01 (lint is advisory; the gate is CI; fix via inline noqa not a shared pyproject.toml), B-REDUND-01 (one broad orientation pass before serial greps). Every numeric threshold lives in the execution-bounds registry (Requirement 20 / task 44), never here (CH-15). *(Reconciliation: closes the dangling 'see actor-independence in CLAUDE.md' short-name references the steering strings depend on; A9 / 05-remediation-spec §A9.)*
  - _Requirements: 11.1, 11.4_ *(Reconciliation 2026-06-16: 11.4 here is task 1's scaffolding tag for the git/.gitignore durable trail; it is NOT a PreCompact→11.4 coverage edge. 11.4 ("record an incremental commit per completed Slice") is owned by the implementer's per-slice commit; PreCompact's genuine REQ-STATE anchors are 11.1 (persist outside model context) and 11.2 (the checkpoint write).)*

  - [ ]* 1.1 Smoke-test scaffold: verify directory structure matches design component inventory
    - Assert all required directories exist; fail fast if any are missing
    - _Requirements: 7.1_

- [ ] 2. `feature_list.schema.json` — Coverage Model Schema
  - [ ] 2.1 Implement `schema/feature_list.schema.json`
    - Write JSON Schema (draft-07) with all required top-level fields: `schema_version`, `product_class`, `checklist_ref`, `items`
    - Define `CoverageItem` definition: `id` (pattern `^[A-Z]+-[A-Z]+-[0-9]{3}$`), `type` enum `{functional,NFR,WIRING}`, `priority`, `dependencies`, `acceptance_criteria` (minItems 1), `status` enum `{unproven,proven,failed}` default `unproven`, optional `evidence` ref
    - Define `EvidenceRecord` definition: all four required fields (`test_file`, `test_name`, `output_hash` with sha256 pattern, `collected_at` date-time), `additionalProperties: false`
    - _Requirements: 5.1, 5.3, 5.6_

  - [ ]* 2.2 Write property test for coverage item schema invariant
    - **Property 1: Coverage Item Schema Invariant**
    - **Validates: Requirements 5.1, 5.4**
    - Use `hypothesis` to generate arbitrary `feature_list.json`-shaped dicts; assert every generated valid item passes schema validation; assert any item with missing required field or wrong `type` enum fails
    - `# Feature: spec-to-evidence-control, Property 1: Coverage Item Schema Invariant`

  - [ ]* 2.3 Write property test for evidence schema enforcement (four-field gate)
    - **Property 2: Evidence Schema Enforcement (Four-Field Gate)**
    - **Validates: Requirements 5.3, 5.6**
    - Generate `EvidenceRecord` dicts with arbitrary field combinations; assert validation passes only when all four fields present and non-empty; assert any single missing/empty field causes validation failure
    - `# Feature: spec-to-evidence-control, Property 2: Evidence Schema Enforcement`

  - [ ] 2.4 Implement the schema negative-validation acceptance (design Phase-0 spine row 1) *(Reconciliation 2026-06-16: non-optional — the component's own stated pass condition ("Schema validates a hand-written valid example; rejects an example missing `output_hash`") had no implementing task; tasks 2.2/2.3 are optional Hypothesis property tests, and the smoke/integration tests (16.1, 17.1) only exercise the hooks/`subagent_stop_hook`'s `output_hash` check, never `jsonschema.validate` against the schema file.)*
    - Write a test that runs `jsonschema.validate` against `schema/feature_list.schema.json`: a hand-written valid `feature_list.json` passes; an item whose `evidence` is missing `output_hash` is rejected
    - _Requirements: 5.1, 5.3, 5.6_

  - [ ] 2.5 Enum-sync consistency test (JSON schema enums vs Postgres CHECK vs spec_validator) *(Reconciliation 2026-06-16: there was no task keeping the three enum sources aligned; `requirements.ears_pattern` is `TEXT NOT NULL` with NO CHECK in the Postgres schema, so that enum can silently drift.)*
    - Assert the JSON schema's `type` enum `{functional, NFR, WIRING}` equals the coverage/requirements Postgres `type` CHECK and the `spec_validator` pattern set
    - Assert the schema's `ears_pattern` enum (5 base patterns) stays in sync with `spec_validator`; flag that `requirements.ears_pattern` (Postgres) has no CHECK and is the drift risk
    - _Requirements: 5.1_

- [ ] 3. `evidence_collector.py` — Evidence_Record Builder
  - [ ] 3.1 Implement `tools/evidence_collector.py`
    - Write `collect(test_file, test_name, output_bytes) -> EvidenceRecord` function: compute `sha256:<hex>` from `output_bytes`, capture timezone-aware ISO-8601 `collected_at` from `datetime.now(timezone.utc).isoformat()` (emits a `+00:00` offset) *(Reconciliation 2026-06-16: was `datetime.utcnow()` — the EvidenceRecord schema requires `format: date-time` (RFC 3339) and `evidence_records.collected_at` is `TIMESTAMPTZ NOT NULL`; a naive `utcnow()` string has no offset, can fail strict date-time validation, and would be coerced to a different instant on Postgres insert, breaking Property 19's "all four fields shall match the original capture values without loss".)*
      - For WIRING items, `collect()` must accept and assemble an **integration-test** artifact (not only a behavioral/Playwright artifact): `output_bytes` is the integration-test result exercising the real execution path (REQ-EXEC-012 / 8.3). For NFR items (REQ-VERIFY-007/008), `output_bytes` is the k6 / Lighthouse / axe-core result artifact. *(Reconciliation 2026-06-16: pins the byte-source for non-test artifacts so the WIRING-proof and NFR-proof paths have an explicit assembly point.)*
    - Write `validate_evidence_record(record: dict) -> bool` that checks all four fields present and non-empty AND validates formats — `output_hash` against the anchored pattern `^sha256:[a-f0-9]{64}$` and `collected_at` as a parseable ISO-8601/RFC-3339 timestamp (or run `jsonschema` against the EvidenceRecord definition); raise `ValueError` listing missing/malformed fields on failure *(Reconciliation 2026-06-16: strengthened from presence-only — the SubagentStop hook calls this same validator, so a non-empty but malformed `output_hash` (uppercase hex, missing `sha256:` prefix, wrong length) previously passed both the validator and the SubagentStop gate. This closes the deferral rationale that the SubagentStop schema-validation gate "already enforces Evidence_Record structure at the hook layer.")*
    - Write `store_to_feature_list(item_id, record, feature_list_path)` that atomically writes evidence and applies the permitted status transition via JSON patch — permitting {`unproven → proven`, `unproven → failed`, `failed → unproven`}; only a transition *into* `proven` requires a complete Evidence_Record (`unproven → failed` / `failed → unproven` require none) *(Reconciliation 2026-06-16: was "flips status to proven … blocked if any field missing", which omitted the `failed`-state edges added in the 2026-06-15 status-edge reconciliation — status enum {unproven, proven, failed}; Property 3.)*
    - _Requirements: 5.3, 5.6, 8.3, 9.3, 25.1, 25.2_ *(Reconciliation 2026-06-16: added 8.3 (REQ-EXEC-012 WIRING integration-test evidence) and 25.1/25.2 (REQ-VERIFY-007/008 NFR Evidence_Record assembly) — the collector is the assembler of those records.)*

  - [ ]* 3.2 Write property test for evidence round-trip (Phase-0 in-memory portion)
    - **Property 19: Evidence Round-Trip (Store and Retrieve)** — Phase-0 in-memory/file portion only
    - **Validates: Requirements 5.3, 5.6**
    - Generate arbitrary `(test_file, test_name, output_bytes)` triples; collect → validate → assert all four fields present and `output_hash` matches SHA-256 of input bytes (no Postgres) *(Reconciliation 2026-06-16: this Phase-0 collector subtask has NO Postgres — `store_to_postgres` is Phase-2 task 30.1. The "stored in Postgres, retrievable by requirement_id and commit_sha" portion of Property 19 (and its Requirements 16.2 mapping) is split out to task 30.2; this subtask validates only the collect→validate→hash-match round-trip against 5.3/5.6.)*
    - `# Feature: spec-to-evidence-control, Property 19: Evidence Round-Trip`

  - [ ]* 3.3 Write unit tests for `evidence_collector.py`
    - Test: `collect()` emits a timezone-aware `collected_at` carrying a `+00:00` offset (asserts the `datetime.now(timezone.utc)` fix, not naive `utcnow()`) *(Reconciliation 2026-06-16)*
    - Test: empty/zero-byte artifact validity — *(Reconciliation 2026-06-16: decide and assert one of (a) `collect()` raises on empty `output_bytes`, or (b) the Verifier must assert the artifact is non-trivial before calling `collect()`.)* `sha256('')` (`e3b0c442...`) is well-formed and passes all four-field/schema/format checks, so a zero-byte artifact would otherwise silently be accepted as proof; the test must assert the chosen reject-empty behavior (or document why empty is acceptable) rather than blessing the meaningless hash. If option (a) changes the collector contract, add a matching note under Requirement 5.3 / 9.3.
    - Test: `collect()` `output_hash` matches the anchored regex `^sha256:[a-f0-9]{64}$` (lowercase hex, `sha256:` prefix present); assert uppercase hex and a missing prefix are rejected
    - Test: `validate_evidence_record()` rejects records missing each of the four fields individually, AND rejects a present-but-malformed `output_hash` (uppercase hex / missing prefix / wrong length) and an unparseable `collected_at` *(Reconciliation 2026-06-16: format validation, not presence-only)*
    - Test: `store_to_feature_list()` rejects transition when evidence incomplete
    - *(Reconciliation 2026-06-16, evidence-quality caveat:)* the sha256/timestamp/format correctness of `collect()` is **unit-test-verified only** and is NOT in the Z3 coverage. The CHECK-7a/7b/7c family operates purely on abstract booleans (`evidenceComplete == And(evidenceHasHash, evidenceHasTestFile, ...)`) — it models the four-field GATE LOGIC, not the collector's actual hashing / `datetime` output / `^sha256:[a-f0-9]{64}$` format. The Z3 "evidence schema enforced" claim must not be mistaken for runtime hash-format coverage. (Z3 count remains 34/34 — no check is added or removed.)
    - _Requirements: 5.3, 5.6_

- [ ] 4. `spec_validator.py` — Z3-Backed EARS Validator
  - [ ] 4.1 Implement `tools/spec_validator.py`
    - Write EARS pattern encoder: map each pattern (Ubiquitous, Event-driven, State-driven, Unwanted, Optional) to Z3 Boolean formula using the SMT-lib translation rules in the design
    - Write `validate_spec(requirements: list[dict]) -> dict` returning `{contradictions, ambiguities, uncovered, violation_count}`
    - Implement consistency check (`check-sat` on full axiom set), completeness check (UNMAPPED detection), vacuity check, and independence check (prediction variables cannot influence gate decisions)
    - Implement vague-adjective scanner: reject any requirement containing `{fast,secure,scalable,optimized,efficient,reliable,performant}` without a numeric bound
    - Set Z3 solver timeout to DEFAULT 60 seconds; return `{violation_count: -1, error: "validator_timeout"}` on timeout
    - _Requirements: 1.2, 1.4, 4.1, 4.2, 4.3_

  - [ ]* 4.2 Write property test for spec validator structured output
    - **Property 14: Spec Validator Returns Structured Output**
    - **Validates: Requirements 4.1**
    - Generate arbitrary requirement lists; assert `validate_spec()` always returns a dict with exactly the four fields `{contradictions, ambiguities, uncovered, violation_count}`; assert authoring agent output is never consulted
    - `# Feature: spec-to-evidence-control, Property 14: Spec Validator Returns Structured Output`

  - [ ]* 4.3 Write property test for EARS pattern assignment uniqueness
    - **Property 16: EARS Pattern Assignment Uniqueness**
    - **Validates: Requirements 1.4**
    - Generate arbitrary requirement strings; assert each validated requirement carries exactly one EARS pattern tag; assert zero-pattern and multi-pattern cases are rejected
    - `# Feature: spec-to-evidence-control, Property 16: EARS Pattern Assignment Uniqueness`

  - [ ]* 4.4 Write property test for vague-adjective rejection
    - **Property 17: Vague-Adjective Rejection**
    - **Validates: Requirements 1.2**
    - Generate requirement strings that embed each vague adjective from the set `{fast,secure,scalable,optimized,efficient,reliable,performant}` in arbitrary positions without a numeric bound; assert all are rejected; assert strings with numeric bounds pass
    - `# Feature: spec-to-evidence-control, Property 17: Vague-Adjective Rejection`

  - [ ]* 4.5 Write unit tests for `spec_validator.py`
    - Reproduce all 34 formal-verification checks from `formal_verification_merged.py` as unit assertions (14 core + 12 Kiro + 8 new; the harness self-counts its groups)
    - Test timeout path: mock Z3 solver to raise `TimeoutError`; assert return value has `violation_count == -1`
    - _Requirements: 4.1, 4.2_

- [ ] 5. `stop_hook.py` — Coverage Gate + Watchdog + Reentrancy Guard
  - [ ] 5.1 Implement `.claude/hooks/stop_hook.py`
    - Implement `load_feature_list()` and `load_run_state()` (reading from `feature_list.json` and `claude-progress.txt` / in-memory fallback before Postgres). *(Reconciliation 2026-06-16, Note N-25: when `db_connection.health_check()` fails the coverage gate MUST fall back to file-backed state (`feature_list.json` + `claude-progress.txt`) and reach the SAME allow/block decision it would on Postgres — (1) file-fallback equivalence, (2) never fail-open, (3) on divergence take the more conservative (blocking) result. See Notes N-25.)*
    - Implement `check_no_progress(run_state, feature_list) -> bool`: count items proven and commits produced across last N=3 slices; fire when both are zero
    - *(Reconciliation 2026-06-18, audit C-IDLE-03 — external-blocker / idle → HANDOFF, evaluated BEFORE the unproven-items block):* Implement `check_external_blocker(run_state) -> bool` reading the loop-driver-populated `run_state.external_blocker` flag (and/or an agent-declared-blocker marker). In `evaluate_stop`, add this as a HANDOFF trigger ALONGSIDE no-progress/cap/budget and evaluate it BEFORE the Check-1 unproven-items exit-2 block: when an external blocker or pure-idle streak is present, write `status=handoff`, emit the HANDOFF summary naming the blocker, and **exit 0 (allow stop)** — never exit 2 and never an idle 'standing by' turn. This is the same surface-and-HANDOFF terminal as cap/budget/no-progress (single canonical HANDOFF contract).
    - Read `run_state.external_blocker` (populated by the loop driver from the A8 goal directive's `BLOCKED-ON: <dependency>` sentinel): WHEN non-empty, `evaluate_stop` SHALL write `status=handoff`, emit a HANDOFF summary naming the blocker, and ALLOW termination (exit 0) — the surface-and-HANDOFF terminal that A8 authorizes, so a self-unsatisfiable blocker becomes a clean HANDOFF, never an idle 'standing by' loop (C-IDLE-03). This is the consumer end of the A8 contract; the producer (sentinel grammar) is task 9.3 and the run_state populator is the loop-driver precondition. *(Reconciliation: pins the A2↔A8 two-ends-of-one-contract handshake — the directive authorizes the agent to stop honestly, this gate lets it stop.)*
    - Implement `evaluate_stop(event) -> HookDecision`: Check 1 — any `unproven` items → **exit 2** (block, force continuation) with enumerated IDs; Check 2 — no-progress fires → write `status=handoff`, emit HANDOFF summary, **exit 0 (allow stop)**; Check 3 — iteration cap (DEFAULT 25) reached → write `status=handoff`, emit HANDOFF summary, **exit 0 (allow stop)**; else → exit 0. *(REQ-LOOP-005: HANDOFF = halt-and-escalate, so it MUST allow the stop; returning exit 2 on cap/no-progress would force-continue and risk an infinite block. Only Check 1 blocks.)*
      - *(Reconciliation: Check-1 block-reason channel + steering content — HGD-1/BP-3, best-practices §1.1 + §2 P1.)* Check 1's exit-2 block MUST write its reason to **STDERR** (NOT stdout — on exit 2 stdout-JSON is ignored and only stderr reaches the model, best-practices G4). The reason MUST point at the deterministic oracle and ONE next step, not a bare verdict: e.g. 'Stop blocked: in-scope item F-12 is unproven — run the verifier subagent on F-12 (it needs a complete 4-field Evidence_Record; proven requires the verifier, not a self-grade).' On a repeat block of the SAME unproven item, vary/escalate the message rather than re-injecting byte-for-byte (escalate-don't-re-inject; 2–3 rungs → HANDOFF), so an identical re-block never re-fires the identical turn. The fail-closed exception path already writes structured error to stderr (below); this bullet covers the normal Check-1 block.
    - Implement `with_reentrancy_guard(event, fn)`: key the re-entry decision on the Claude-Code hook-INPUT payload flag `event.stop_hook_active` (read from the Stop event JSON on stdin) — when it is `true`, return `allow()` immediately emitting ZERO tokens and do NOT cascade. *(Reconciliation 2026-06-18, audit TWL-02/BP-2/CH-07: do NOT gate on a self-authored `run_state.stop_hook_active` mutex — a self-set/clear mutex races the loop and can wedge stuck-true on a crash/non-allow path. The durable `run_state.stop_hook_active` mirror is written for observability/REQ-GATE-004 (Req 10.4) only and is NOT the re-entry signal.)*
    - *(Reconciliation 2026-06-18, audit C-LOOP-04/CH-10 — escalate-don't-re-inject ladder, REQ-LOOP-006/Req 14.5):* Implement the bounded escalation ladder in `evaluate_stop`: track a loop-driver-populated `run_state.block_streak` (the count of consecutive re-entries on the SAME blocking condition). On a re-entry that the reentrancy guard short-circuits, emit ZERO tokens (no reason re-injection). When the block IS re-evaluated, VARY the steering message per rung (rung 1: located defect + next action; rung 2: 'blocked the same way N times — narrow to X'; rung 3: 'still blocked — HANDOFF imminent') and on `block_streak >= BLOCK_ESCALATION_CAP` (DEFAULT 3, read from `tools/execution_bounds`, literal-3 fallback) route to HANDOFF (`status=handoff`, exit 0). NEVER re-emit a byte-for-byte identical reason. Keep `BLOCK_ESCALATION_CAP` under Claude Code's ~8-9x force-override so governance hands off FIRST.
    - *(Reconciliation 2026-06-16: tasks the helpers `evaluate_stop` references but were previously untasked.)* (5.1b) Implement `emit_handoff_summary(...)` honoring the HANDOFF-summary content contract: remaining unproven in-scope item IDs, the last N=3 slice outputs, and the HANDOFF reason (cap / budget / no-progress)
    - (5.1c) Implement `write_run_state(run_state)` / `save_run_state(run_state)` persistence (writes `status`, `no_progress_n`, `stop_hook_active` to the durable store with `claude-progress.txt` file-backed duplicate per Note N-25)
    - (5.1d) Implement the slice-history counters `count_items_proven_since(...)` and `count_commits_since(...)` used by `check_no_progress` (count over the last N=3 slices); both feed the budget branch in `evaluate_stop`
    - Wrap entire hook in `try/except`; on unhandled exception exit 2 (fail closed) with structured error to stderr
    - _Requirements: 4.2, 4.3, 4.4, 10.2, 10.4, 13.5, 14.1, 14.2_ *(Reconciliation 2026-06-16: added 13.5 — Hook Exit-Code Contract (Property 21): exit 0 = proceed, exit 2 = blocking via stderr, exit 1 does NOT block — this hook is the canonical emitter of that contract (exit-0 allow/COMPLETE/HANDOFF vs exit-2 block). NOTE on 4.3: the strict-decrease no-progress check is the spec-completion loop / Initializer's responsibility — `evaluate_stop` reads only the scalar `run_state.violation_count` and has no access to the PRIOR pass's count to compute a pass-over-pass strict decrease; 4.3 is retained here only for the no-progress→HANDOFF routing, NOT a per-pass strict-decrease comparator inside the Stop hook.)*

  - [ ]* 5.2 Write property test for stop hook — unproven blocks termination
    - **Property 5: Stop Hook — Unproven Blocks Termination**
    - **Validates: Requirements 5.5, 10.2**
    - Generate feature lists with arbitrary mixes of `unproven`/`proven` items; assert hook blocks (exit 2) when any item is `unproven`; assert hook allows (exit 0) only when zero items are `unproven`
    - `# Feature: spec-to-evidence-control, Property 5: Stop Hook — Unproven Blocks Termination`

  - [ ]* 5.3 Write property test for no-progress → HANDOFF only
    - **Property 8: No-Progress → HANDOFF Only**
    - **Validates: Requirements 14.2**
    - Generate run states with arbitrary `no_progress_n` values and slice histories; assert that when both conditions (zero proven, zero commits) hold for N=3 slices the status transitions to `handoff` never `complete`
    - Treat N as an integer threshold (the configured DEFAULT N=3 window): assert the transition fires at exactly `no_progress_n >= 3`, not before, and not for non-integer/arbitrary values
    - Assert the hook EXITS 0 (allows termination) on the HANDOFF path, not exit 2 *(Reconciliation 2026-06-15: REQ-LOOP-005 — HANDOFF must allow the stop; only the unproven-items case blocks with exit 2)*
    - `# Feature: spec-to-evidence-control, Property 8: No-Progress → HANDOFF Only`

  - [ ]* 5.4 Write property test for cap and budget → HANDOFF only
    - **Property 9: Cap and Budget → HANDOFF Only**
    - **Validates: Requirements 14.1, 14.2**
    - Generate run states at or beyond the iteration cap or cost budget; assert terminal status is always `handoff`; assert `complete` and `handoff` are never simultaneously true
    - Assert the hook EXITS 0 (allows termination) on the HANDOFF path, not exit 2 *(Reconciliation 2026-06-15: REQ-LOOP-005 — cap/budget HANDOFF must allow the stop; only the unproven-items case blocks with exit 2)*
    - `# Feature: spec-to-evidence-control, Property 9: Cap and Budget → HANDOFF Only`

  - [ ]* 5.5 Write unit tests for `stop_hook.py`
    - Test reentrancy guard: call hook twice concurrently; assert second call returns allow immediately
    - Test: unhandled exception in body → exits 2 with error message
    - *(Reconciliation 2026-06-18, audit C-LOOP-04/C-IDLE-03):* Test re-entry signal: call the hook with a Stop payload carrying `stop_hook_active: true` on stdin → assert it returns allow (exit 0) emitting ZERO bytes of reason (no re-injection), and assert the decision does NOT consult `run_state.stop_hook_active`. Test escalation ladder: drive `run_state.block_streak` 1→2→3 on the same condition → assert the steering message VARIES per rung (no byte-identical re-injection) and that `block_streak >= BLOCK_ESCALATION_CAP` routes to HANDOFF (status=handoff, exit 0). Test external-blocker/idle: with `run_state.external_blocker` true AND an unproven in-scope item present → assert HANDOFF (exit 0) wins over the exit-2 unproven block and no idle 'standing by' output is produced.
    - _Requirements: 10.4, 13.5_ *(Reconciliation 2026-06-16: added 13.5 — the unit test asserts the Hook Exit-Code Contract (exit 0 allow / exit 2 block-with-stderr / fail-closed-on-exception exit 2) for this hook's canonical emitter.)*

- [ ] 6. `pre_tool_use_hook.py` — Plan Gate + Scope Gate + Artifact Guard + Status Guard
  - [ ] 6.1 Implement `.claude/hooks/pre_tool_use_hook.py`
    - Implement `check_plan_approval(event) -> Optional[HookDecision]`: block any `Write`/`Edit`/`MultiEdit` call if `plan-approved.json` missing; also verify `feature_list_sha` in approval matches current `feature_list.json` SHA-256
    - Implement `check_scope_sequencing(event) -> Optional[HookDecision]`: block any `Bash` worktree-create or slice-assign call if any prior-slice item in `feature_list.json` is `unproven`
      - *(Reconciliation 2026-06-16: pin the exact detection surface so the gate cannot be bypassed.)* Detect the worktree-create/slice-assign command forms precisely: Bash invocations matching `git worktree add`, the `tools/worktree_manager.py` create entry points (`create_worktree`), and the slice-assign command surface; cover the tool surfaces these can arrive on. Add a property test for bypass forms (worktree created via a wrapper script or a non-Bash tool). NOTE: CHECK-6a proves only the abstract `scopeGateBlocks` boolean — NOT the concrete command-detection patterns; the patterns are unit/property-tested only, not Z3-checked.
    - Implement `check_artifact_guard(event) -> Optional[HookDecision]`: block any tool targeting `feature_list.json` schema, `tests/`, CI config, or executing destructive Bash patterns (`rm -rf`, `DROP TABLE`, `git reset --hard`)
      - *(Reconciliation: content-level protected-path Bash check — HGD-2, best-practices §3 G8.)* The artifact guard MUST treat a **Bash command that WRITES a protected path** as a protected-artifact edit, not only the destructive patterns above. A `Write|Edit|MultiEdit`-only mental model is bypassed by shell writes (claude-code #63787: the model reaches for `tee` to bypass its own Write guard) — parse the `Bash` `tool_input.command` and block (exit 2) when it would create/modify a path under `tests/`, `schema/feature_list.schema.json`, or CI config via any write form: shell redirection (`>`, `>>`), `tee`, in-place edit (`sed -i`, `perl -i`), `cp`/`mv`/`install`/`dd of=` into the path, or an interpreter heredoc/`-c` write (`python -c`, `python - <<`, `node -e`). The PreToolUse hook is registered with NO matcher (design Hook Configuration block — no `matcher` key on the PreToolUse entry), so it already sees `Bash`; this bullet makes the guard's path-write detection cover the `Bash` surface, closing the `tee`/`sed -i`/`echo >` bypass. Add a property test for each bypass form. NOTE: unit/property-tested only, not Z3-checked (CHECK proves only the abstract `artifactGuardBlocks` boolean).
    - Implement `check_status_transition(event) -> Optional[HookDecision]`: for any write to `feature_list.json`, validate the proposed transition is in the permitted set {`unproven → proven`, `unproven → failed`, `failed → unproven`} and block all other edges (identity mutations, into-`proven` without evidence, any edge outside the set); only a transition *into* `proven` additionally requires a complete Evidence_Record (`unproven → failed` and `failed → unproven` require none) *(Reconciliation 2026-06-16: widened from "unproven → proven only" to match the 2026-06-15 status-edge reconciliation — status enum {unproven, proven, failed}; Property 3.)*
    - *(Reconciliation 2026-06-16:)* Implement `check_schema_validation(event) -> Optional[HookDecision]`: load `schema/feature_list.schema.json` and JSON-Schema-validate every `feature_list.json` write (e.g. via `jsonschema.validate`); block (exit 2) on any schema-invalid write (e.g. an item with `status: proven` but a missing `output_hash`). This realizes the design-mandated "PreToolUse validates writes against the schema" behavior, which `check_status_transition` (transition-edge + evidence completeness only) does not cover.
    - *(Reconciliation 2026-06-16: wire REQ-SPEC-016 / Property 27 / CHECK-12 into the hook — the design hook-wiring checklist-approval row, Property 27, and CHECK-12 exist but no build task previously named this guard.)* Implement `check_checklist_approval(event) -> Optional[HookDecision]`: for an initializer/discovery `Write` that references a domain-baseline checklist, block (exit 2) unless the referenced checklist has a non-null `approved_at` in `domain_baseline_checklists`. Cross-reference Property 27 / CHECK-12a-12b (task 50 implements the abstract gate logic; this bullet names the concrete PreToolUse hook check).
    - *(Reconciliation: block-reason channel + steering content — HGD-1/BP-3, best-practices §1.1 + §2.)* On every BLOCK each guard MUST write its reason to **STDERR** and exit 2 — NEVER print the reason to stdout (Claude Code feeds stderr to the model on a block and IGNORES stdout-JSON on exit 2, so a stdout reason is invisible to the agent and it flails / routes around the guard — best-practices G4). The reason string MUST (a) name the located oracle — the actual field/path/actor + its current value (e.g. `status` flip by `actor_agent=implementer`, or the protected path `tests/test_login.py`), keyed on model SHAPE not product content; (b) give exactly ONE corrective next step the agent can take THIS turn on a path some other gate ALLOWS (e.g. 'route this status flip through the verifier subagent; do not edit feature_list.json.status directly' / 'edit the implementation under your slice, or HANDOFF'); and (c) for the two actor-authority denies (status guard, artifact guard) carry an anti-workaround clause forbidding the bypass ('do NOT write this via Bash redirection / tee / sed -i; surface the change to a human or the verifier' — best-practices G8/P9). Keep it generalizable (right altitude, best-practices P3), not a brittle if/then transcript. (Stop block-reason content is the parallel task-5.1 edit, HOOKGEN-07.)
    - Chain the guards in this explicit, deterministic order and return the first blocking decision: **integrity-guard (task 49.1) → plan → scope → artifact → status → schema-validation → checklist-approval** (and the secret-block once added); wrap in `try/except` with exit 2 on exception (fail closed) *(Reconciliation 2026-06-16: replaces the prior "chain all four checks" — task 49.1 chains the resumed-state integrity guard BEFORE plan/scope/artifact/status, and the checklist-approval and schema-validation checks have no slot in a four-check chain. Order is pinned here so the 6+-guard build is deterministic; gates are evaluated in order and short-circuit on the first block.)*
    - _Requirements: 5.2, 5.3, 5.6, 7.4, 7.5, 13.2, 13.3, 13.4, 18.1_ *(Reconciliation 2026-06-16: added 5.6 — the four-field/non-empty Evidence_Record gate is mapped to the PreToolUse status guard in design's hook-wiring table (REQ-COV-002/003/006) but was previously not traced to this task. NOTE on 12.3: REQ-OBS-003 gate-decision OTel telemetry (event, tool, allow/block, reason, requirement ID) is a binding obligation on this hook's decisions but the emission is implemented in task 36.1 (Phase 3, which already names PreToolUse) — Phase-0/1 PreToolUse runs without decision telemetry by acknowledged deferral. NOTE on REQ-AUDIT-001: audit-log production (`audit_log.append` on every allow/block) is deferred to task 52.3 (Phase 2); the Phase-0 PreToolUse plan gate does NOT produce audit entries — REQ-AUDIT-001 completeness begins at 52.3. NOTE on Postgres-unavailable fallback (design hook-wiring "Postgres unavailable" row + Note N-25): the scope gate (reads prior-slice statuses), the status/schema guard (reads/validates `feature_list.json`), and the integrity guard (reads `run_state.resume_integrity_ok`) MUST fall back to file-backed state (`feature_list.json` + `claude-progress.txt`) and reach the SAME conservative/blocking decision, never fail-open.)*

  - [ ]* 6.2 Write property test for plan approval gate
    - **Property 6: Plan Approval Gate**
    - **Validates: Requirements 7.4, 18.1**
    - Generate `(tool_name, plan_file_exists, sha_matches)` triples; assert hook blocks any Write/Edit/MultiEdit when `plan_file_exists=False` or `sha_matches=False`; assert hook allows only when both true
    - `# Feature: spec-to-evidence-control, Property 6: Plan Approval Gate`

  - [ ]* 6.3 Write property test for scope sequencing gate
    - **Property 7: Scope Sequencing Gate**
    - **Validates: Requirements 7.5**
    - Generate feature lists with arbitrary subsets of items marked `unproven`; assert worktree-create is blocked whenever any prior item is `unproven`; assert it is allowed only when all prior items are `proven`
    - `# Feature: spec-to-evidence-control, Property 7: Scope Sequencing Gate`

  - [ ]* 6.4 Write property test for identity mutation blockade
    - **Property 3: Identity-Mutation Blockade**
    - **Validates: Requirements 5.2, 13.3**
    - Generate tool calls that attempt to delete, reorder, or change `id`/`type`/`acceptance_criteria` of existing items; assert all are blocked; assert the permitted status edges {`unproven → proven` (requires a complete Evidence_Record), `unproven → failed`, `failed → unproven`} are allowed and all other transitions (identity mutations, into-`proven` without evidence, any edge outside the set) are blocked *(Reconciliation 2026-06-16: was "only `status: proven` writes are allowed", which would wrongly fail a legitimate `unproven → failed` / `failed → unproven` write — status enum {unproven, proven, failed}; Property 3.)*
    - `# Feature: spec-to-evidence-control, Property 3: Identity-Mutation Blockade`

  - [ ]* 6.5 Write unit tests for `pre_tool_use_hook.py`
    - Test each of the four check functions independently with boundary inputs
    - Test: exception in any check → exits 2, never exits 0
    - _Requirements: 13.4, 13.5_

- [ ] 7. `session_start_hook.py` — State Loader
  - [ ] 7.1 Implement `.claude/hooks/session_start_hook.py`
    - Read `git status --porcelain` output and format as structured summary
    - Read `claude-progress.txt` (create with empty state if absent)
    - Read and parse `feature_list.json` (create minimal valid stub if absent); compute count of `unproven` vs `proven` items
    - Inject combined summary into Claude Code context via stdout as **structured JSON** with the named fields `git_status`, `unproven_count`, `proven_count` (informational only — exit 0 always) *(Reconciliation 2026-06-16: pin the output shape — integration test 17.1 asserts these JSON fields, while smoke test 16.1 is the looser "contains git/progress/coverage summary" check; this bullet single-sources the contract as the named-JSON-field form so both tests assert the same fidelity.)*
    - Wrap in `try/except`; on failure log warning to stderr and exit 0 (non-blocking)
    - *(Reconciliation 2026-06-16: cross-reference — the Phase-2 resumed-state-integrity extension of this Phase-0 hook is tasked at subtask 49.2 below; it imports `tools/state_integrity.py`, computes the resumed-state hash, and writes `run_state.resume_integrity_ok`, remaining non-blocking (exit 0 always).)*
    - _Requirements: 11.3_

  - [ ]* 7.2 Write unit tests for `session_start_hook.py`
    - Test: on first-run (no progress file, no feature_list.json) → exits 0 with stub summary
    - Test: with populated `feature_list.json` → summary includes correct unproven count
    - Test: on resume, `run_state.resume_integrity_ok` is written (per the Phase-2 task-49.2 extension) *(Reconciliation 2026-06-16)*
    - _Requirements: 11.3_

  - [ ] 7.3 Spine-registration canary + re-orientation injection (A5) *(Reconciliation: closes the silent-unwiring gap — no task asserted the governance hooks are actually registered; C-HOOK-01/C-INTENT-02.)*
    - Read the active hook registration (parse the resolved `settings.json` / runtime hook config) and compare the registered event set against `SPINE_REQUIRED_EVENTS` (DEFAULT = the five A1 events: `SessionStart`, `PreToolUse`, `PostToolUse`, `SubagentStop`, `Stop`; env-overridable). Inject `Spine wired: N governance event(s) registered` (green) on full match; inject a LOUD `GOVERNANCE SPINE UNWIRED/PARTIAL: <missing>` warning on any miss/malformed config.
    - Scope `SPINE_REQUIRED_EVENTS` to the 5 A1-registered events — NOT 6 — so the canary is green when the spine is wired as-scoped; PreCompact is excluded until a registered PreCompact hook is added to settings.json (COH-2). Document this scoping in a comment so it is intentional, not forgotten.
    - Inject a re-orientation block: current branch (`git rev-parse --abbrev-ref HEAD`), in-scope `unproven`/`proven` counts, and the last HANDOFF reason from `run_state`. All via the exit-0 stdout `additionalContext` channel — informational, never blocking (CH-12).
    - Fail OPEN with a diagnostic line on any internal error; exit 0 always.
    - _Requirements: 11.5_

  - [ ]* 7.4 Unit test the spine canary *(Reconciliation: A5)*
    - Test: all 5 A1 events registered → stdout contains `Spine wired: 5 governance event(s) registered` and NO `UNWIRED/PARTIAL` token.
    - Test: `Stop` missing from the registered set → stdout contains `GOVERNANCE SPINE UNWIRED/PARTIAL` naming `Stop`; exit 0 (non-blocking).
    - Test: PreCompact absent does NOT trip the canary (outside `SPINE_REQUIRED_EVENTS`, COH-2).
    - Test: injected context includes the branch, in-scope unproven/proven counts, and the last HANDOFF reason.
    - _Requirements: 11.5_

- [ ] 8. `subagent_stop_hook.py` — Evidence Schema Validator
  - [ ] 8.1 Implement `.claude/hooks/subagent_stop_hook.py`
    - Parse subagent result from stdin (JSON); locate `evidence` field(s) within result
    - Call `validate_evidence_record()` from `evidence_collector.py` on each evidence record
    - If any field missing or empty: exit 2 with enumerated missing fields (fail closed)
    - If all records valid: exit 0
    - Wrap in `try/except`; exit 2 on unhandled exception
    - *(Reconciliation 2026-06-18, HGD-4 — actor resolved server-side, NOT from the payload.)* The acting agent MUST be resolved via `tools.actor_identity.resolve_identity(event).actor_agent` (which reads `CLAUDE_AGENT_NAME` from the harness env + the stdin `session_id`, per actor_identity.py:44), NEVER from a payload-supplied `actor_agent` key — an agent-written `actor_agent` is untrusted and is deliberately ignored. The role-separation check then BLOCKS (exit 2) any evidence-bearing result whose resolved actor is `implementer.md` (Property 24, the implementer may not self-verify — design.md SubagentStop obligation #3) and any record whose payload `actor_agent` does not equal the resolved actor (`actor_forged`). Compare the resolved actor against the single-source `VERIFIER_ROLE` constant (edit AI-03), not a local byte-literal.
    - *(Reconciliation 2026-06-18, HGD-4 / COH-3 — emit a VALID SubagentStop decision value.)* When the hook emits a JSON decision object, the block value MUST be a valid SubagentStop value — **`block`** (or omit the `decision` field entirely to allow) — NOT the literal `"approve"` (which is NOT a valid SubagentStop decision and is read as a no-op, silently letting a self-graded result through). If any existing helper/test asserts the legacy `"approve"`/`"allow"` accept literal (e.g. `tests/spine/test_subagent_stop_actor.py`), update it in lockstep. The hard block remains stderr-on-exit-2.
    - _Requirements: 9.5, 9.2 (Property 24 role separation)_

  - [ ]* 8.2 Write unit tests for `subagent_stop_hook.py`
    - Test: subagent result with complete Evidence_Record → exits 0
    - Test: subagent result missing `output_hash` → exits 2 naming `output_hash`
    - Test: subagent result with zero evidence fields → exits 2
    - _Requirements: 9.5_

- [ ] 9. `settings.json` Hook Wiring
  - [ ] 9.1 Write `.claude/settings.json` (or `.kiro/settings.json`) with all hook registrations
    - Register `Stop`, `PreToolUse`, `PostToolUse` (matcher: `Write|Edit|MultiEdit`), `SubagentStop`, `SessionStart`, `PreCompact` — all as `"type": "command"`
    - Verify NO hook uses `"type": "http"` or `"type": "mcp"` (fail-closed requirement)
    - *(Reconciliation 2026-06-16: the command-type registration is WHY `subagent_stop_hook.py` can fail closed (exit 2) at all — REQ-STEER-004 (13.4) requires command-type hooks; no HTTP/MCP for hard policy. The task-9.2 smoke test `tests/smoke/test_hook_config.py` parses `settings.json` and asserts EVERY registered hook including SubagentStop is command-type with no http/mcp.)*
    - *(Reconciliation 2026-06-18, audit C-LOOP-04/C-HOOK-01 — ralph-loop disable, the #1 anti-loop root cause):* ALSO write a project-scoped `enabledPlugins` block setting `"ralph-loop@ralph-loop": false`, so the `ralph-loop` plugin's `stop-hook.sh` cannot run in parallel with — and shadow — the governance `Stop` hook (the merged-Stop-hooks-run-in-parallel mechanic that produced the 49x identical re-injection). The project-scoped `false` MUST out-rank the user-level enable; add a `_comment_ralph_loop` documenting the operator fallback (run with the plugin off / remove it from `~/.claude/settings.json → enabledPlugins`) if it still appears in telemetry.
    - _Requirements: 13.4 (REQ-STEER-004)_

  - [ ]* 9.2 Smoke-test hook config: assert all hooks are command-type
    - Write `tests/smoke/test_hook_config.py`: parse `settings.json`; assert every registered hook has `"type": "command"`; assert no HTTP/MCP hooks present *(Reconciliation 2026-06-16: explicitly includes SubagentStop — this is the test that proves SubagentStop's command-type fail-closed property, REQ-STEER-004.)*
    - *(Reconciliation 2026-06-18, audit C-LOOP-04/TWL-06 — ralph-disable assertions, static + runtime):* (static) assert `settings.json` `enabledPlugins["ralph-loop@ralph-loop"] == false`. (runtime telemetry) add a smoke assertion that after a governed Stop event the hook telemetry shows the governance `stop_hook.py` ran AND `stop-hook.sh` (the ralph-loop plugin Stop hook) is ABSENT from the telemetry — the governance `Stop` hook owns the event; `stop-hook.sh` firing in a governed session is a hard failure.
    - _Requirements: 13.4 (REQ-STEER-004)_

  - [ ] 9.3 Author the bounded-autonomy goal directive (A8) — top-level steering string read by the model *(Reconciliation: the producer of `run_state.external_blocker` that the Stop hook already consumes; closes C-IDLE-03.)*
    - Author `.claude/goal-directive.md` (or the project's top-level/system steering string) as a read-once-per-session declarative contract: authorize self-continuation ONLY when the next step is in-scope (`in_scope == true`) AND objectively checkable (≥1 machine-checkable AC); otherwise surface-and-HANDOFF.
    - Define the `BLOCKED-ON: <dependency>` sentinel: on a self-unsatisfiable blocker the loop emits exactly one `BLOCKED-ON: <dependency>` line; the loop driver / `run_state` populator parses it into `run_state.external_blocker`, which `stop_hook.py`'s `evaluate_stop` reads to route to HANDOFF (Req 21 / REQ-LOOP-005). NOTE: the parser/populator is a loop-driver precondition (the D3 run_state field maintenance), not this task — this task DEFINES the sentinel grammar and contract.
    - Pair anti-fabrication with its terminal: forbid 'standing by' / fabricated-progress continuations; an idle turn with zero proven progress and no `BLOCKED-ON:` sentinel is the no-progress condition, not a valid self-continuation.
    - Reference durable invariants by short name (actor-independence, verifier-only flips, human-owned artifacts, canonical-source pin) inherited from the root `CLAUDE.md` anchor (task 1 / A9), never restated inline (CH-15).
    - _Requirements: REQ-ORCH-005 (15.0a–0c), 14.2, 21.1_

  - [ ]* 9.4 Test the goal-directive contract *(Reconciliation: A8)*
    - Test: a synthesized `BLOCKED-ON: missing-tool` line is parsed to `run_state.external_blocker == 'missing-tool'` and `evaluate_stop` routes to HANDOFF (exit 0), not a block.
    - Test: an idle turn with zero proven flips and no `BLOCKED-ON:` sentinel is counted toward the N=3 no-progress window (not treated as self-continuation).
    - _Requirements: 14.2, 21.1_

- [ ] 10. Subagent definitions (`.claude/agents/`)
  - [ ] 10.1 Write `.claude/agents/initializer.md` — Spec Compiler + Coverage Model Builder
    - Define role, permissions (read/write spec artifacts + `feature_list.json` + baselines; no access to `tests/`, CI, or `src/`), and key behaviors
    - Include: run `spec_validator.py` after every elaboration pass; loop bounded to DEFAULT=7 passes; flag UNMAPPED items; write all items defaulting to `unproven`; enter plan mode; do NOT write `plan-approved.json`
    - *(Reconciliation 2026-06-16: three behaviors that the requirement map below newly traces to this agent.)* Add behaviors: (i) **trigger the Research subagent** when the detected product class has no approved checklist (3.1 — initializer triggers Research_Sub_Agent on a new/undefined product class); (ii) **emit WIRING and NFR coverage items as first-class entries** (not comments) per Property 1 "Validates 5.1, 5.4" (5.4); (iii) **emit a non-null `omission_declaration`** enumerating, by EARS scenario category {Primary / Alternate / Exception / Recovery / Non-Functional / Edge-Case}, every scenario class not covered, each with a `[Gap]` marker (29.1 / REQ-SPEC-018)
    - *(Reconciliation 2026-06-16, config-module dependency:)* the bounded spec-completion loop (DEFAULT 7 passes, `SPEC_COMPLETION_HARD_CAP`) and the Z3 validator timeout (DEFAULT 60s) are READ from the centralized execution-bounds config module built in task 44 (which lists "loop 7, timeout 60s" among its operator-overridable DEFAULTs) — the initializer consumes but does not own these thresholds
    - *(Reconciliation 2026-06-16, decompose into testable steps with acceptance checks — the initializer carries the heaviest requirement load yet its only acceptance test was the single hand-run.)* Decompose authoring into steps, each with an acceptance check: (a) spec-compile to EARS + atomic IDs; (b) validator-loop with 7-pass cap and strict-decrease no-progress → HANDOFF; (c) discovery + UNMAPPED flagging; (d) provenance marking (stated / inferred) with per-inferred-item human confirmation gating before items enter `feature_list.json` (Req 2.3 — not only bulk plan-mode review); (e) WIRING / NFR first-class emission (5.4); (f) `feature_list.json` seed + populate; (g) plan-mode handoff without writing `plan-approved.json`; (h) `omission_declaration` emission (29.1). Add a behavioral fixture beyond the single hand-run.
    - Include HANDOFF conditions: no-progress (count doesn't decrease) → immediate HANDOFF; pass cap reached → HANDOFF
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 2.1, 2.2, 2.3, 3.1, 4.1, 4.2, 4.3, 4.4, 4.5, 5.1, 5.4, 18.2, 29.1 (REQ-SPEC-018)_ *(Reconciliation 2026-06-16: added 3.1 (triggers Research on a new product class — previously mapped only on research task 10.4), 5.4 (WIRING/NFR first-class coverage items per Property 1), and 29.1 / REQ-SPEC-018 (non-null `omission_declaration` on initializer output).)*

  - [ ] 10.2 Write `.claude/agents/implementer.md` — Coding Subagent
    - *(Reconciliation 2026-06-16: `implementer.md` does not yet exist on disk (`.claude/agents/` holds only a 0-byte `.gitkeep`) yet it is Phase-0 spine component #8 with acceptance test "Creates worktree; commits with requirement ID in trailer".)* The file MUST be authored per the Claude Code agent spec with YAML frontmatter (`name: implementer`, `description`, `model`, and a `tools`/allowed-tools allowlist) BEFORE any Phase-0 smoke (task 16.1) or e2e loop can run. Cross-link the design implementer.md section and the spine acceptance row.
    - Define role, permissions (write to implementation source in assigned worktree only; no write to `tests/`, `feature_list.json` schema, CI, or other worktrees), and key behaviors
    - Include: read `feature_list.json` for highest-priority `unproven` item; create dedicated git worktree; target ≤15 min / ≤1 feature; produce one atomic commit with requirement ID in trailer; do NOT run verification
    - *(Reconciliation 2026-06-16, kill-switch instrumentability — REQ-CTRL-001:)* the implementer (and the other three agents) is a **kill-switchable agent entry point**: its slice-start capability is checked against the flagd kill-switch flag (task 57) before a slice starts, so REQ-CTRL-001.2's "disable the affected agent capability within ≤30s without process restart" has a concrete instrumentation point on this agent.
    - *(Reconciliation 2026-06-18, COH-1 name convention.)* The frontmatter `name:` MUST carry the `.md` suffix — **`name: implementer.md`** — to match the runtime `CLAUDE_AGENT_NAME` convention the actor gates resolve and compare (the verifier peer is `verifier.md`; the role-separation gate in `subagent_stop_hook.py` blocks any evidence-bearing result whose resolved `actor_agent == "implementer.md"`, so the literal must agree byte-for-byte). Replace the `name: implementer` shown above (tasks.md:233) with `name: implementer.md`; design.md:270 carries the matching suffix.
    - *(Make the no-self-grade boundary a first-class, testable authority bullet, not prose.)* The prompt MUST state, as an explicit PROHIBITION: the implementer **never flips `status`, never assembles or returns an Evidence_Record, and never self-verifies** — it returns the committed slice to the Verifier with NO evidence (Property 24). The `tools:` allowlist is `[Read, Grep, Glob, Edit, Write, Bash]` (design.md:273) with `Write`/`Edit` CONFINED to the slice worktree by the sandbox (REQ-17.4, task 46); NO `tests/`, `schema/`, CI, or other-worktree write. Add to the task-10.2 smoke test (`tests/smoke/test_agent_frontmatter.py`) an assertion that `name == "implementer.md"`.
    - _Requirements: 7.1, 7.2, 7.3, 6.2_

  - [ ] 10.3 Write `.claude/agents/verifier.md` — Independent Evaluator
    - *(Reconciliation 2026-06-16: `verifier.md` does not yet exist on disk (`.claude/agents/` holds only a `.gitkeep`), yet the design cites `perf_a11y_verifier` as a "capability within `.claude/agents/verifier.md`". Author this file so that citation is not dangling.)*
    - Define role, permissions (read-only on `src/`; read/write on `tests/` and `feature_list.json` status field only; no write to implementation source), and key behaviors
    - Include: structural checks (lint, type check, AST), semantic checks (unit + integration tests), behavioral checks (Playwright CLI → capture trace/screenshot), security checks (Semgrep + CodeQL), assemble Evidence_Record via `evidence_collector.py`, flip `unproven → proven` only when all checks pass and coverage ≥ 85%
    - **Forward reference:** the fifth (performance / accessibility + UI-screen-render) verification layer is added to THIS file in task 51 (the `perf_a11y_verifier` capability) — task 51 amends `.claude/agents/verifier.md` rather than creating a separate component *(Reconciliation 2026-06-16)*
    - *(Reconciliation 2026-06-18, COH-1 frontmatter-name convention — LOAD-BEARING.)* The frontmatter `name:` MUST be the EXACT byte string the live gates compare against — **`name: verifier.md`** (WITH the `.md` suffix), NOT `name: verifier`. The Claude Code runtime populates `CLAUDE_AGENT_NAME` from this `name:` (`tools/actor_identity.py:44`), and `tools.actor_identity.resolve_identity` + every actor gate (`subagent_stop_hook.py:30` `VERIFIER_AGENT`, `pre_tool_use_hook.py:25` `VERIFIER_AGENT`, `tools/store.py:95`, `tools/coverage.py:21`) key on the literal `verifier.md`. A suffix-less `name: verifier` resolves `actor_agent == "verifier" != "verifier.md"`, so EVERY legitimate `unproven → proven` flip is rejected as `actor_not_verifier` and the agent is fail-closed-but-stuck (master remediation spec §3.2 COH-1, apply step 0). This makes the design-frontmatter example (design.md:299 currently shows `name: verifier`) consistent with the on-disk gate literal `verifier.md` — the on-disk literal is canonical; design's frontmatter block and the peer agent files (10.1/10.2/10.4) carry the matching suffix (`initializer.md`, `implementer.md`, `research.md`).
    - *(Authority checklist — make the verifier's three exclusive authorities first-class, testable bullets, not prose.)* The prompt MUST state, as enumerated authorities: (a) the verifier is the **SOLE producer of an Evidence_Record**; (b) the verifier is the **SOLE actor that flips `status` into `proven`** (every other role and `main` are blocked at PreToolUse + SubagentStop); (c) it runs in a session **distinct from the implementer's** and never repairs the code it attests. The `tools:` allowlist MUST be `[Read, Grep, Glob, Bash]` with NO `Write`/`Edit`/`MultiEdit` (the `tests/` + `feature_list.json`-status writes flow through the PreToolUse artifact-guard `verifier.md` carve-out, per design.md:294/302 — not a broad Write grant).
    - Add the task-10.3 smoke test `tests/smoke/test_agent_frontmatter.py`: parse `.claude/agents/verifier.md`, assert `name == "verifier.md"` (suffix present), assert the `tools` allowlist contains no `Write`/`Edit`/`MultiEdit`, and assert the resolved `CLAUDE_AGENT_NAME` for this agent equals the gates' `VERIFIER_ROLE` (cross-ref task-44 single-source constant, edit AI-03).
    - _Requirements: 9.1, 9.2, 9.3, 9.6_

  - [ ] 10.4 Write `.claude/agents/research.md` — Domain-Baseline Checklist Sourcer
    - *(Reconciliation 2026-06-16, frontmatter + web-tool grant:)* author the agent with explicit Claude Code frontmatter (`name`, `description`, `model`, `tools`). Because the agent MUST query web sources (competitive-analysis + standards + OSS references), its `tools:` MUST grant a web-search/fetch capability (e.g. `WebSearch` / firecrawl) sufficient for those queries — resolving the scope-vs-behavior contradiction where the agent was granted only `baselines/` read-write with no web/network tool. The design Permissions line is correspondingly updated to grant the web/network tool alongside `baselines/` read-write.
    - Define role, permissions (read/write to `baselines/` **plus a web-search/fetch tool grant**; no access to `src/`, `tests/`, or CI), and key behaviors
    - Include: triggered by Initializer on new product class; query competitive analysis + standards + OSS refs; produce draft checklist named by product class under `baselines/`; present for human review; do NOT use checklist until approved; persist approved checklist as version-controlled artifact
    - *(Reconciliation 2026-06-16, phase-ordering / gate-deferral constraint:)* this agent is built in the Phase-0 parallel wave but its epistemic-integrity gate (task 50, REQ-SPEC-016/017), its omission-declaration gate (task 54, REQ-SPEC-018), and its checklist-approval tests (39.17 / 39.19) all land in Phase 3+. To prevent an un-gated DRAFT checklist or unlabeled/unfact-checked DRAFT claims from being used during Phase 0–2, **research must NOT be INVOKED on an un-gated product class until tasks 50/54 land** — research.md's research-invocation path is gated by tasks 50/54. This Phase-0-build / Phase-3-gate deferral is intentional and is recorded here and in the Notes.
    - *(Reconciliation 2026-06-18, COH-1 name convention.)* The authored frontmatter `name:` MUST be **`name: research.md`** (with the `.md` suffix), matching the runtime `CLAUDE_AGENT_NAME` convention used by the peer agents and the actor gates (verifier.md / implementer.md). (tasks.md:247-249 specify generic frontmatter `name`/`description`/`model`/`tools` but pin no literal — pin the suffix here.)
    - *(Make the epistemic-integrity authorities first-class, testable bullets — REQ-SPEC-017/018, mirrors design.md:314-316 and the A7 research.md prompt.)* The prompt MUST require: (a) **every external claim carries a `source_url` AND an `authority_tier` label** (enum `primary-standard` / `peer-reviewed` / `vendor-doc` / `oss-reference` / `blog`) AND passes an **independent fact-check** before the draft is presented for human review — unlabeled/unverified claims are rejected by `research_claim_validator.py` (task 50, Property 29, design.md:159); (b) the draft checklist is **unusable until `approved_at` is non-null** (a DRAFT cannot drive discovery — PreToolUse checklist-approval guard, CHECK-12, design.md:219); (c) the research output emits a **non-null, non-EMPTY `omission_declaration`** enumerating, by EARS scenario category {Primary / Alternate / Exception / Recovery / Non-Functional / Edge-Case}, every scenario class NOT covered, each `[Gap]`-marked (validated against `schema/subagent_output.schema.json`; rejected by the SubagentStop omission_guard if null/absent, REQ-SPEC-018, design.md:225/316). The `tools:` allowlist MUST grant a web-search/fetch tool (`WebSearch`/`WebFetch` or firecrawl) PLUS `baselines/` read-write, and nothing on `src/`/`tests/`/CI.
    - Add to the agent-frontmatter smoke test: assert `name == "research.md"`.
    - _Requirements: 3.1, 3.2, 3.3_

- [ ] 11. Git worktree wiring scripts
  - [ ] 11.1 Write `tools/worktree_manager.py`
    - Implement `create_worktree(item_id: str) -> str`: run `git worktree add .worktrees/{item_id} -b slice/{item_id}`; return worktree path
    - Implement `remove_worktree(item_id: str)`: run `git worktree remove --force .worktrees/{item_id}` after merge/abandon
    - Implement `list_active_worktrees() -> list[str]`: parse `git worktree list --porcelain`
    - Enforce: one worktree per active slice; fail if worktree already exists for `item_id`
    - _Requirements: 7.2, 7.3_

  - [ ]* 11.2 Write integration tests for worktree wiring
    - Test: `create_worktree` → `git worktree list` shows exactly one entry for `item_id`
    - Test: `remove_worktree` → worktree no longer listed
    - Test: duplicate create for same `item_id` → raises error
    - _Requirements: 7.2_

- [ ] 12. `feature_list.json` initializer — empty coverage model
  - [ ] 12.1 Write `tools/feature_list_init.py`
    - Implement `initialize_feature_list(product_class, checklist_ref) -> dict`: produce a minimal valid `feature_list.json` with `schema_version: "1.0.0"`, empty `items: []`, and provided `product_class` / `checklist_ref`
    - Validate the produced file against `schema/feature_list.schema.json` before writing to disk
    - Write the validated file atomically (write to temp, then `os.replace`)
    - _Requirements: 5.1_

  - [ ]* 12.2 Write unit tests for `feature_list_init.py`
    - Test: initialized file passes schema validation
    - Test: file with missing `checklist_ref.sha` fails schema validation
    - _Requirements: 5.1_

- [ ] 13. Wire `formal_verification_merged.py` as CI check
  - [ ] 13.1 Create `.github/workflows/formal-verification.yml`
    - Trigger on `push` and `pull_request`
    - Install `z3-solver` via pip; run `python3 verification/formal_verification_merged.py` *(Reconciliation 2026-06-16: corrected the invocation path — the harness lives at `verification/formal_verification_merged.py` on disk, not repo-root, so the prior `python3 formal_verification_merged.py` would fail file-not-found in CI. The DEPRECATED `docs/superseded/formal_verification.py` is never invoked.)*
    - Fail workflow if exit code is non-zero (any assertion failure)
    - Register as a required status check in GitHub repository ruleset
    - _Requirements: 4.1_

  - [ ]* 13.2 Smoke-test: verify `formal_verification_merged.py` currently exits 0
    - Run `python3 verification/formal_verification_merged.py` in CI; assert exit 0 (all 34 checks pass: 14 core + 12 Kiro + 8 new) *(Reconciliation 2026-06-16: corrected invocation path to `verification/formal_verification_merged.py` per the on-disk location.)*
    - _Requirements: 4.1_

- [ ] 14. GitHub Actions coverage gate (OPA/Conftest stub for Phase 0)
  - [ ] 14.1 Create `.github/workflows/coverage-gate.yml`
    - Trigger on `pull_request`
    - Install OPA/Conftest; run `conftest test feature_list.json --policy .github/policies/` 
    - For Phase 0: write a minimal `coverage_query.rego` stub that passes only when `feature_list.json` contains zero `unproven` items (full Postgres-backed policy deferred to Phase 1 task 21) *(Reconciliation 2026-06-16: was "task 20" — task 20 is `orphan_detector.py`; the full `coverage_query.rego` policy is task 21. Note the Phase-0 stub (status-only, passes on zero unproven) is intentionally WEAKER than the Phase-1 full policy (which adds evidence-presence checks), so Phase-0 green does NOT imply Phase-1 green — the `coverage-gate` required-status-check registration must survive the stub→full swap (re-register; do not assume continuity).)*
    - Register as a required status check in GitHub repository ruleset
    - _Requirements: 10.3_

  - [ ] 14.2 Configure GitHub repository ruleset
    - **This bullet is the single canonical enumeration of required status checks** *(Reconciliation 2026-06-16: tasks 40.2/40.3/40.4/45 and the design `docs/github-ruleset.md` description SHALL reference this list rather than re-listing checks, so the merge-gate set is single-sourced and cannot drift across the three prior locations.)* Document (in `docs/github-ruleset.md`) the required status checks: `formal-verification`, `coverage-gate`, `secrets-scan` (task 45), `audit-chain-verify` (task 52), `traceability-gate` (task 40.4), `zap-baseline` (task 56), `deepeval-gate` (task 55), `sast-semgrep` (Phase-1 task 24), `sast-codeql` (Phase-1 task 23), the SonarCloud New-Code check (Phase-1 task 22; register the EXACT SonarCloud-reported context name read off a live run — NOT a guessed `coverage-gate-sonar`), plus human PR reviewer requirement *(Reconciliation 2026-06-15: secrets-scan and audit-chain-verify are REQUIRED merge gates; 2026-06-16: traceability-gate added as the blocking caller that consumes `orphan_detector.py`'s non-zero exit — REQ-6.3 "block the run"; 2026-06-16: added `zap-baseline` (REQ-SEC-008.2) and `deepeval-gate` (REQ-EVAL-001.3) — both declared REQUIRED at merge in requirements/design, previously omitted from the doc list; 2026-06-23 Phase-1: added `sast-semgrep` (REQ-DEPTH-003, fork-safe OSS — the binding SAST check on fork PRs), `sast-codeql` (REQ-DEPTH-002, same-repo-only), and the SonarCloud New-Code gate (REQ-DEPTH-004, same-repo-only) — the SAST/quality depth gates. RT-04: each context is the workflow job `name:` VERBATIM (`sast-codeql`/`sast-semgrep`/`traceability-gate`); SonarCloud sets its own name, confirm it from a live run before registering. The actual `gh api` ruleset PUT + CodeQL/Sonar `main` baseline seeding are OWNER ACTIONS — they require the new workflows to have run at least once so the contexts exist, and are remote-system mutations (see docs/github-ruleset.md "Strengthening").)*
    - _Requirements: 10.3, 18.3_

- [ ] 15. Playwright CLI integration in CI
  - [ ] 15.1 Add Playwright step to `.github/workflows/coverage-gate.yml`
    - Install `playwright` and `playwright install chromium`
    - Run `playwright test tests/smoke/` (smoke suite to be populated by Verifier agent during slice verification)
    - Upload trace file as workflow artifact on failure
    - _Requirements: 9.1, 9.3_

- [ ] 16. Phase 0 Smoke Test — end-to-end spine
  - [ ] 16.1 Write `tests/smoke/test_spine_e2e.py`
    - Create a trivial `feature_list.json` with one `unproven` item and one `proven` item (with valid Evidence_Record)
    - Call `stop_hook.py` via subprocess with the `unproven`-containing file → assert exit 2
    - Call `stop_hook.py` with all-`proven` file → assert exit 0
    - Call `pre_tool_use_hook.py` with Write tool and no `plan-approved.json` → assert exit 2
    - Call `session_start_hook.py` → assert exit 0 and stdout contains the git/progress/coverage summary *(Reconciliation 2026-06-16: this is the looser smoke "contains" check by design; the structured-JSON-field assertion (`git_status`, `unproven_count`, `proven_count`) is owned by integration test 17.1 against the single-sourced task-7.1 contract.)*
    - Call `subagent_stop_hook.py` with complete Evidence_Record → assert exit 0; with missing `output_hash` → assert exit 2
    - _Requirements: 5.5, 7.4, 9.5, 10.2, 11.3_

- [ ] 17. Phase 0 end-to-end integration test
  - [ ] 17.1 Write `tests/integration/test_phase0_integration.py`
    - Create a temp git repo with a `feature_list.json` containing one `unproven` and one fully-evidenced `proven` item
    - Call `stop_hook.py` via subprocess against the mixed file; assert exit 2 and stderr names the unproven item ID
    - Call `stop_hook.py` against an all-proven file; assert exit 0
    - Call `pre_tool_use_hook.py` with a `Write` event and no `plan-approved.json`; assert exit 2
    - Write a valid `plan-approved.json` with matching SHA; call hook again with `Write` event; assert exit 0
    - Call `pre_tool_use_hook.py` with a worktree-create event while a prior item is `unproven`; assert exit 2
    - Call `session_start_hook.py`; assert exit 0 and stdout JSON contains `git_status`, `unproven_count`, `proven_count`
    - Call `subagent_stop_hook.py` with a complete 4-field Evidence_Record; assert exit 0
    - Call `subagent_stop_hook.py` with `output_hash` missing; assert exit 2 and error names `output_hash`
    - Run `python3 verification/formal_verification_merged.py`; assert exit 0 *(Reconciliation 2026-06-16: corrected invocation path to `verification/formal_verification_merged.py` per the on-disk location.)*
    - _Requirements: 4.2, 5.5, 7.4, 7.5, 9.5, 10.2, 11.3, 13.5_

---

### Phase 1 — Verification Depth

- [ ] 18. `post_tool_use_hook.py` — Lint + SAST + Wiring Feedback
  - [ ] 18.1 Implement `.claude/hooks/post_tool_use_hook.py`
    - Triggered on `Write`, `Edit`, `MultiEdit` completion
    - Run lint (e.g., `ruff check`) on changed files; run type check (`mypy`); capture stdout/stderr
    - Run `semgrep --config auto` on changed files; filter for HIGH/CRITICAL findings
    - Run `python3 tools/wiring_checker.py` on changed files
    - *(Reconciliation 2026-06-16, changed-files handoff contract):* derive the changed-file list from the hook payload — `tool_input.file_path` for `Write`/`Edit`, and the full set of edited paths for `MultiEdit` (one `MultiEdit` call can mutate multiple files; the matcher is `Write|Edit|MultiEdit` per design) — and pass them to `wiring_checker.py` as argv, one file path per positional argument.
    - Collect all findings; emit to stdout as structured feedback; exit 1 (non-blocking, next-turn feedback only — never exit 2)
    - Wrap in `try/except`; exit 1 on exception (non-blocking)
    - _Requirements: 9.4, 13.2_

  - [ ]* 18.2 Write unit tests for `post_tool_use_hook.py`
    - Test: clean file → exits 1 with empty findings list (still non-blocking)
    - Test: file with lint error → exits 1 with lint finding in output
    - Test: exception in body → exits 1 (never exits 2)
    - _Requirements: 9.4, 13.2_

- [ ] 19. `wiring_checker.py` — Call-Graph / Dead-Code Analysis
  - [ ] 19.1 Implement `tools/wiring_checker.py`
    - Accept a list of changed files as CLI args — exact argv format is one file path per positional argument (the set the PostToolUse hook derived from `tool_input.file_path` for `Write`/`Edit` or the edited-path set for `MultiEdit`; see task 18.1's changed-files handoff contract) *(Reconciliation 2026-06-16)*
    - Use Python AST (`ast` module) to build a call graph for each file: map function/method definitions to their call sites
    - Identify functions/methods that are never called from any real execution path (dead code)
    - For each dead-code finding, emit a WIRING coverage item candidate (JSON to stdout) with `type: "WIRING"` and the unreachable symbol name
    - *(Reconciliation 2026-06-16, division of labor with task 24.1):* `wiring_checker.py` (AST) covers plain defined-but-never-called functions; `wiring_dead_code.yml` (Semgrep, task 24.1) covers decorator-routed handlers/routes and registered-but-uninvoked callbacks; both emit `type: "WIRING"` candidates, de-duplicated by symbol before ingestion. This resolves which tool authoritatively detects the route/handler/callback obligations named in criterion 8.2 and prevents double-reporting.
    - Exit 0 even when findings exist (findings are returned to caller; blocking is done by `post_tool_use_hook.py`)
    - _Requirements: 8.1, 8.2_

  - [ ]* 19.2 Write unit tests for `wiring_checker.py`
    - Test: file with reachable route handler → no WIRING finding
    - Test: file with defined but never-called function → emits WIRING finding
    - _Requirements: 8.1_

  - [ ] 19.3 WIRING-candidate ingestion path (satisfies criterion 8.1's second clause) *(Reconciliation 2026-06-16: the `wiring_checker.py` candidate previously stopped at stdout/next-turn text and no task turned it into a coverage item.)*
    - Specify the actor and write path that "represents each wiring obligation as a WIRING coverage item in `feature_list.json`": the implementer/initializer, on receiving the `wiring_checker.py` candidate as PostToolUse next-turn feedback (task 18.1), MUST add a `type: "WIRING"` CoverageItem (`status` default `unproven`, `in_scope` true, ≥1 acceptance criterion per Property 1) to `feature_list.json` via the PreToolUse status-guard-permitted creation path
    - _Requirements: 8.1 (REQ-EXEC-010)_

- [ ] 20. `orphan_detector.py` — Bidirectional Orphan Check
  - [ ] 20.1 Implement `tools/orphan_detector.py`
    - Scan all source files for requirement ID references matching `[A-Z]+-[A-Z]+-[0-9]{3}` in comments, docstrings, and commit trailers
    - *(Reconciliation 2026-06-16, run scope / glob / language):* (1) run scope is **full-repo** (CI-suited; this is the blocking traceability-gate caller in task 40.4, unlike the changed-files `wiring_checker.py`/PostToolUse pipeline); (2) file glob = Python source, with an exclude list (`tests/`, generated dirs, `__init__.py`, `db/migrations/`); (3) language scope is Python source only — this bounds false positives and determines where it can be wired.
    - *(Reconciliation 2026-06-16, ID-regex match scope):* the regex matches the canonical 3-segment `CoverageItem.id` form `[A-Z]+-[A-Z]+-[0-9]{3}` (unanchored within comments/trailers — e.g. `REQ-TRACE-001`, `REQ-VERIFY-007`, `REQ-SPEC-018`), explicitly **NOT** the dotted EARS criterion numbers (e.g. `6.3`), which are a different namespace the same regex cannot match. Confirm it matches all `REQ-<DOMAIN>-NNN` IDs present in `feature_list.json`.
    - *(Reconciliation 2026-06-16, shared trailer helper):* factor the `[A-Z]+-[A-Z]+-[0-9]{3}` commit-trailer extraction into one shared helper (e.g. `tools/req_id_scan.py`) imported by BOTH this tool and `traceability_writer.py` (task 29.1) to prevent regex drift/double-maintenance. Authority split: `traceability_writer.assert_commit_has_req_id` owns the commit-has-req-id gate (REQ-6.2 / Property 10); `orphan_detector` owns bidirectional orphan detection (REQ-6.3 / Property 11).
    - Read `feature_list.json` for all known requirement IDs
    - *(Reconciliation 2026-06-16, authoritative store for the backward-orphan verification-artifact lookup):* the canonical source is **Postgres** (single source of truth for coverage queries, REQ-16.3) — query `evidence_records` / `traceability_links` (`link_type IN ('test','evidence')`) for the verification-artifact link, with a documented `feature_list.json` fallback consistent with the Postgres-unavailable fallback rule (Note N-25). Reading `feature_list.json` alone can diverge.
    - *(Reconciliation 2026-06-16, "verification artifact" definition):* a **backward orphan** = a requirement ID with **NO** `traceability_links` row of `link_type IN ('test','evidence')` AND/OR no `evidence_records` row. This is the canonical pass/fail boundary the check keys on (mirror this definition into Property 11).
    - *(Reconciliation 2026-06-16, forward-orphan exemption/allowlist):* provide an explicit ignore mechanism so the forward-orphan rule does not fail-noisy on legitimately un-annotated units (helpers, `__init__.py`, config, generated code) — a `# orphan-exempt: <reason>` inline marker AND/OR a config file of excluded paths; define granularity (file-level via path config, function-level via inline marker). Without this the check is unimplementable as a non-noisy blocking gate.
    - Report: (a) source files/functions with no requirement ref (forward orphans); (b) requirement IDs with no source file or verification artifact (backward orphans, per the canonical definition above)
    - Exit non-zero and emit structured JSON report when any orphan is found
    - *(Reconciliation 2026-06-16, blocking caller):* this non-zero exit is consumed by the REQUIRED `traceability-gate` CI workflow (task 40.4), which fails the merge on any orphan — the production "block the run" mechanism for REQ-6.3 (previously the exit was consumed only by test task 26.1).
    - _Requirements: 6.3_

  - [ ]* 20.2 Write property test for orphan detection
    - **Property 11: Orphan Detection**
    - **Validates: Requirements 6.3**
    - Generate source-file/requirement pairs with arbitrary coverage; assert detector always flags (a) any impl unit with no req ref and (b) any req with no verification artifact; assert both conditions independently trigger failure
    - *(Reconciliation 2026-06-16, canonical backward-orphan definition):* a backward orphan = a requirement ID with NO `traceability_links` row of `link_type IN ('test','evidence')` AND/OR no `evidence_records` row; assert exempted units (`# orphan-exempt: <reason>` marker or allowlisted path) do NOT count as forward orphans.
    - `# Feature: spec-to-evidence-control, Property 11: Orphan Detection`

- [ ] 21. `coverage_query.rego` — Full OPA Zero-Evidence Merge Policy
  - [ ] 21.1 Implement `.github/policies/coverage_query.rego` (full policy, replacing Phase 0 stub)
    - Write Rego policy: deny merge if any requirement ID in the approved set has zero rows in `evidence_records`
    - Accept `feature_list.json` as Conftest input; the deny rules iterate **only over items where `in_scope == true`** (filter `input.items` on `in_scope == true` before any status/evidence check, mirroring `evaluate_stop`'s `in_scope_items` and Req 5.7) and deny merge if any such item has `status != "proven"` (anything not exactly `proven` blocks — a `failed` in-scope item also blocks, matching the Stop hook's `not_proven = [i for i in in_scope_items if i.status != "proven"]`) *(Reconciliation 2026-06-16: was "reads `items[_].status == "unproven"`" — that naive rule both wrongly blocked on out-of-scope unproven items (diverging from the Stop gate) and silently passed a `failed` in-scope item; status enum is {unproven, proven, failed}.)*
    - Add second rule: deny if any in-scope item has `status == "proven"` but its `evidence` object is missing OR any of the four Evidence_Record fields (`test_file`, `test_name`, `output_hash`, `collected_at`) is absent or empty *(Reconciliation 2026-06-16: enumerated the four fields explicitly — the vague "missing or has empty fields" wording could pass a proven item carrying a partial 1-field evidence object that the SubagentStop four-field check / Property 2 would reject, an inconsistency between the merge gate and the in-session gate.)*
    - Write fixture files under `tests/integration/opa/`: one passing fixture (all in-scope items proven with complete 4-field evidence), one failing fixture (one in-scope unproven item)
    - _Requirements: 5.7, 10.3_

  - [ ]* 21.2 Write property test for OPA zero-evidence policy at merge
    - **Property 22: OPA Zero-Evidence Policy at Merge**
    - **Validates: Requirements 10.3**
    - Generate `feature_list.json` variants with arbitrary proven/unproven/failed and in_scope distributions; assert Conftest policy denies merge whenever any **in-scope** item has `status != "proven"` or any in-scope proven item lacks a complete 4-field Evidence_Record; assert out-of-scope items never trigger denial; assert policy allows only when every in-scope item is proven with complete evidence *(Reconciliation 2026-06-16: aligns Property 22 with the in_scope filter, the `status != "proven"` deny rule, and the four-field evidence enumeration applied to task 21.1)*
    - `# Feature: spec-to-evidence-control, Property 22: OPA Zero-Evidence Policy at Merge`

  - [ ]* 21.3 Write integration tests for OPA/Conftest policy
    - Run `conftest test` against passing and failing fixtures; assert correct pass/fail behavior
    - _Requirements: 10.3_

  - [ ] 21.4 Re-confirm the swapped policy is still the gating one *(Reconciliation 2026-06-16: task 21 replaces the `.rego` content (stub→full) but no task previously verified the swapped policy is still invoked and required.)*
    - Confirm `.github/workflows/coverage-gate.yml` (created in task 14.1) invokes the Phase-1 **full** policy after the stub→full swap (not the Phase-0 stub)
    - Confirm `coverage-gate` remains in the GitHub repository ruleset's required checks (cross-ref task 14.2) — the required-status-check registration must survive the swap; re-register, do NOT assume continuity (the Phase-0 stub is intentionally weaker than the Phase-1 full policy, so Phase-0 green does not imply Phase-1 green)
    - *(Co-tenancy note for traceability):* the single required status check `coverage-gate` co-hosts three independent tools in `.github/workflows/coverage-gate.yml` — OPA/Conftest (task 14.1), Playwright (task 15.1), and SonarCloud (task 22.1). Because all three run under one check name, a Playwright or SonarCloud failure blocks merge under the same name, so the OPA policy is NOT independently gating; REQ-GATE-003's "THE OPA_Conftest required CI status check SHALL run" is satisfied only as a co-tenant. Either document this co-tenancy explicitly (done here) so the OPA leg's gating role is traceable, or split the OPA policy into its own job/required check so it gates independently.
    - _Requirements: 10.3_

- [ ] 22. SonarCloud AI Code Assurance quality gate in CI
  - [ ] 22.1 Add SonarCloud scan step to `.github/workflows/coverage-gate.yml`
    - Add `sonarcloud-github-action` step (or equivalent) with project key configured
    - Configure quality gate: fail on any new HIGH/CRITICAL finding or coverage drop below 85%
    - _Requirements: 9.1, 9.6_

- [ ] 23. CodeQL SAST in GitHub Actions
  - [ ] 23.1 Create `.github/workflows/codeql.yml`
    - Use `github/codeql-action/analyze` for Python
    - Trigger on `push` and `pull_request`
    - Fail on HIGH/CRITICAL severity findings
    - _Requirements: 9.1, 17.1_

- [ ] 24. Semgrep custom rules for WIRING dead-code patterns
  - [ ] 24.1 Write `tools/semgrep_rules/wiring_dead_code.yml`
    - Define Semgrep rule to detect functions decorated with route/handler decorators (e.g., `@app.route`, `@router.get`) that are never imported or called from a non-test entry point
    - Define rule for callbacks registered in a dict/list but never invoked
    - Test rules against synthetic fixtures in `tests/fixtures/semgrep/`
    - *(Reconciliation 2026-06-16, division of labor with task 19.1):* Semgrep here owns decorator-routed handlers/routes and registered-but-uninvoked callbacks; `wiring_checker.py` (AST, task 19.1) owns plain defined-but-never-called functions. Both emit `type: "WIRING"` candidates de-duplicated by symbol before ingestion (no double-reporting of the same 8.1/8.2 obligation).
    - _Requirements: 8.1, 8.2_

- [ ] 25. `pre_compact_hook.py` — PreCompact Checkpoint
  - [ ] 25.1 Implement `.claude/hooks/pre_compact_hook.py`
    - Before context compaction: append current progress summary (item IDs, status counts) to `claude-progress.txt`
    - Checkpoint the current `feature_list.json` evidence state by committing `feature_list.json` itself *(Reconciliation 2026-06-16: dropped the orphan `claude-progress-evidence-snapshot.json` — it appeared exactly once in the spec (this write) and had no reader; SessionStart re-orients from `claude-progress.txt` + `feature_list.json`. The checkpointed set is now {`claude-progress.txt`, `feature_list.json`}, matching the design PreCompact row and giving every written file a reader.)*
    - Write the durable baseline `run_state.resume_state_hash` over the now-checkpointed state — `sha256` over the canonical projection of in-scope `feature_list.json` items + the named `run_state` fields, using the SAME canonical-form / hash algorithm as `tools/state_integrity.py` (design.md run_state DDL `resume_state_hash` column; Property 26). This makes PreCompact the PRODUCER of the recorded baseline that the SessionStart resume-integrity compare reads back — without this write the comparison input never exists and `resume_integrity_ok` always lands on the 'no checkpoint hash to compare' branch (COH-2 / D7). *(Reconciliation: task 25.1 previously only checkpointed files; design.md SessionStart/PreCompact hook-wiring rows, the Phase-0 spine row, the run_state DDL `resume_state_hash` comment, and backlog ASCP-E7-REQ11 ALL already credit PreCompact with writing `resume_state_hash` — this closes that spec-internal contradiction.)*
    - Commit the checkpoint via `git add claude-progress.txt feature_list.json && git commit -m "chore: PreCompact checkpoint [skip ci]"` if anything has changed *(Reconciliation 2026-06-16: dropped the misleading `-f` — neither `claude-progress.txt` nor `feature_list.json` is gitignored (no `.gitignore` entry for them), and `feature_list.json` must remain tracked so SessionStart can read it back; force-add would have implied these files are ignored.)*
    - Exit 0 always (non-blocking checkpoint)
    - _Requirements: 11.2, REQ-STATE-005_

  - [ ]* 25.2 Write unit tests for `pre_compact_hook.py`
    - Test: hook writes progress checkpoint and exits 0
    - Test: hook does not fail if git has no changes to commit
    - Test: hook writes `run_state.resume_state_hash`, and that value equals the `tools/state_integrity.py` recomputation over the same checkpointed state (the baseline producer is wired so SessionStart's resume compare has a non-NULL hash to read; COH-2 / D7) *(Reconciliation: A5 resume-integrity depends on this producer)*
    - _Requirements: 11.2, REQ-STATE-005_

- [ ] 26. Phase 1 verification integration test
  - [ ] 26.1 Write `tests/integration/test_phase1_integration.py`
    - Create a Python source file with a defined-but-never-called function; run `wiring_checker.py` against it; assert JSON output contains a WIRING finding with `type: "WIRING"` and the symbol name
    - Create a source file with no requirement ID comment and a `feature_list.json` with one requirement; run `orphan_detector.py`; assert exit non-zero and report contains both orphan types
    - Write a `feature_list.json` with one `unproven` item; run `conftest test` against `.github/policies/coverage_query.rego`; assert policy denies
    - Write a `feature_list.json` with all `proven` items and complete evidence; run `conftest test`; assert policy passes
    - Run `post_tool_use_hook.py` against a file with a lint error; assert exit 1 (non-blocking) and stdout contains the error message
    - _Requirements: 6.3, 8.1, 8.2, 9.4, 10.3, 13.2_ *(Reconciliation 2026-06-16: added 6.3 — this is the only task whose body actually runs `orphan_detector.py` and asserts both orphan types, so it owns the 6.3 orphan-detection coverage edge; task 33.1's body never invokes `orphan_detector` (it exercises `parse_commit_trailers`/migrations/evidence/run-state), so the 6.3 forward link belongs here.)*

---

### Phase 2 — Durable State

- [ ] 27. Neon Postgres provisioning and connection management
  - [ ] 27.1 Write `tools/db_connection.py`
    - Implement `get_connection() -> psycopg2.Connection`: read `DATABASE_URL` from environment; support Neon serverless endpoint (SSL required); raise `ConfigError` if `DATABASE_URL` unset
    - Implement `health_check() -> bool`: run `SELECT 1`; return True/False; used as fallback-to-file trigger
    - Document in `docs/postgres-setup.md`: Neon project creation, per-PR branching setup, `DATABASE_URL` secret registration in GitHub Actions
    - _Requirements: 16.1_

- [ ] 28. Postgres schema migrations
  - *(Reconciliation 2026-06-18, applied-vs-authored honesty: the eight 001-008.sql files now EXIST and are git-tracked. This task's deliverable is AUTHORING the migration files + DEFINING a tracked idempotent apply path (28.10/28.11). APPLIED state — 'all eight tables created' — is asserted ONLY by the test-branch integration assertions (28.9/33.1), which actually run the runner. No task or AC may claim the durable tables exist in a live database absent that integration run. REQ-INFRA-005 (Plane backlog) AC#4 is reframed in lockstep to depend on authored-files + a defined apply path, not produced tables.)*
  - [ ] 28.1 Write migration `db/migrations/001_requirements.sql`
    - `requirements` table with all columns and CHECK constraints as per design schema
    - _Requirements: 16.1_

  - [ ] 28.2 Write migration `db/migrations/002_coverage_items.sql`
    - `coverage_items` table with FK to `requirements`, status CHECK, default `unproven`
    - Add boolean column `in_scope` NOT NULL DEFAULT true; an item leaves scope only via a human-authored transition, and all completion/Stop gates count ONLY `in_scope` items *(Reconciliation 2026-06-15: in-scope is data, mirroring the `in_scope` field added to the CoverageItem JSON schema)*
    - _Requirements: 16.1_

  - [ ] 28.3 Write migration `db/migrations/003_traceability_links.sql`
    - `traceability_links` table with FK to `requirements`, `link_type` and `direction` CHECK constraints
    - _Requirements: 6.1, 16.1_

  - [ ] 28.4 Write migration `db/migrations/004_evidence_records.sql`
    - `evidence_records` table with FK to `requirements`, `evidence_complete` CHECK constraint enforcing no empty fields
    - Include column `actor_agent TEXT NOT NULL` — MUST be the Verifier, never the Implementer (Property 24) *(Reconciliation 2026-06-16: previously omitted; a builder following the task would drop `actor_agent` and silently break Property 24 (role separation) and the Property 19 round-trip. `actor_agent` lives only on this 7-column Postgres row, NOT on the 4-field EvidenceRecord JSON object, which is `additionalProperties: false`.)*
    - Add a `UNIQUE (requirement_id, commit_sha, test_name)` constraint (or at minimum an index on `(requirement_id, commit_sha)`) so duplicate evidence rows for the same requirement/commit/test are rejected and the Property 19 lookup is indexed *(Reconciliation 2026-06-16: without it, duplicate inserts are silently allowed and can inflate the Property 22 OPA COUNT.)*
    - _Requirements: 5.3, 5.6, 9.2, 16.1_ *(Reconciliation 2026-06-16: added 9.2 for the `actor_agent` role-separation column.)*

  - [ ] 28.5 Write migration `db/migrations/005_run_state.sql`
    - `run_state` table with `status` CHECK `{running,complete,handoff,blocked}`, `stop_hook_active` boolean, `no_progress_n` counter, `resume_integrity_ok BOOLEAN` (REQ-STATE-005; written by SessionStart task 49.2, read by the PreToolUse integrity guard task 49.1), `violation_count INTEGER DEFAULT 0`, `retry_count INTEGER DEFAULT 0` *(Reconciliation 2026-06-16: the design run_state DDL declares `resume_integrity_ok`, `violation_count`, and `retry_count`; these durable columns were previously un-tasked here.)*
    - Add the two escalation/blocker counters the steering-audit A2 Stop-hook ladder consumes (remediation-spec §7.1 D3 / §7.2 item 2): `block_streak INTEGER NOT NULL DEFAULT 0` (consecutive Stop/SubagentStop blocks on the SAME unresolved condition — drives the bounded 3-rung escalate-then-HANDOFF ladder so a block is varied/escalated, never re-injected; the C-LOOP-04 49x-re-injection fix) and `external_blocker TEXT` (NULL = none; set to a short blocker code when the blocking condition is outside the agent's control, routing the Stop hook to HANDOFF-not-block per C-IDLE-03). Both are READ by `stop_hook.py`/`subagent_stop_hook.py` and WRITTEN per-turn by the run_state populator (new task 31.2). Without these columns the escalate-don't-re-inject ladder and external-blocker→HANDOFF paths have no durable state and default inert. *(Reconciliation 2026-06-18: closes the D3 run_state-completeness gap — block_streak/external_blocker are named by remediation §7.2 item 2 as consumed-but-unpopulated and are ABSENT from this 005_run_state.sql DDL; budget_exceeded and resume_state_hash are already handled — budget via the computed token_cost_usd>=TOKEN_BUDGET predicate, resume_state_hash as an existing column.)*
    - _Requirements: 11.1, 16.1, REQ-STATE-005_

  - [ ] 28.6 Write migration `db/migrations/006_domain_baseline_checklists.sql`
    - `domain_baseline_checklists` table with `UNIQUE (product_class, version)`, `approved_at` nullable
    - _Requirements: 3.2, 16.1_

  - [ ] 28.7 Write migration `db/migrations/007_requirement_versions.sql` *(Reconciliation 2026-06-15: 7th table, supports task 48 — requirement-amendment versioning / REQ-COV-007)*
    - `requirement_versions` table mirroring the canonical DDL: `requirement_id` (FK to `requirements`), `version` INTEGER (monotonically increasing), `prior_text` (nullable), `new_text TEXT NOT NULL`, `author TEXT NOT NULL`, `rationale TEXT NOT NULL`, `created_at TIMESTAMPTZ DEFAULT now()`, `UNIQUE (requirement_id, version)`; on amendment the linked coverage item re-enters `unproven` and COMPLETE is blocked while any amended item is un-reproven. Re-proof is observed via `coverage_items.status` flipping back (NOT a column on this table) *(Reconciliation 2026-06-16: was non-canonical `amended_at`/`amendment_reason` + a standalone 're-proven flag' column, which described a different table than the design DDL; renamed `amended_at`→`created_at`, `amendment_reason`→`rationale`, added `prior_text`/`new_text`/`author`, and dropped the re-proven flag.)*
    - _Requirements: 22 (REQ-COV-007); 16.1 (durable storage)_ *(Reconciliation 2026-06-16: was "16.1 (REQ-COV-007)" — Req 16 is REQ-STORE-001..003 durable storage; the REQ-COV-007 amendment obligation is Requirement 22.)*

  - [ ] 28.8 Write migration `db/migrations/008_gate_audit_log.sql` *(Reconciliation 2026-06-15: 8th table, supports task 52 — tamper-evident gate-decision audit log / REQ-AUDIT-001..003)*
    - `gate_audit_log` append-only table: `seq` (monotonic), `event_name`, `tool_name`, `decision`, `reason`, `requirement_id`, `actor_agent`, `created_at`, `prev_hash`, `entry_hash`
    - Genesis entry uses `prev_hash = sha256("")` (empty-string digest) as a documented sentinel; `entry_hash = sha256(canonical_row || prev_hash)` over deterministic JSON of `(seq, event_name, tool_name, decision, reason, requirement_id, actor_agent, created_at)` — entry_hash INCLUDES `seq` and `created_at`
    - **DB-enforce append-only** (not advisory): emit `REVOKE UPDATE, DELETE ON gate_audit_log FROM <app_role>;` plus a `BEFORE UPDATE OR DELETE` trigger that RAISEs an exception, so a superuser/agent cannot silently mutate rows and tamper-evidence is not detection-only *(Reconciliation 2026-06-16: append-only was asserted but never enforced.)*
    - **Seq reconciliation on DB-down:** because `seq` (BIGSERIAL) is part of the hashed canonical form but does not exist in the file backend, specify the reconciliation rule so the file-time `entry_hash` is reproducible — EITHER (a) use a client-generated monotonic seq (UUIDv7 / hybrid logical clock) that survives both backends and is what gets hashed, OR (b) file-era `entry_hash`es are explicitly recomputed and re-chained against the DB-assigned seq on reconnect (and `audit_verify` treats the reconnect boundary accordingly) *(Reconciliation 2026-06-16: reconciliation was previously undefined; pairs with Notes N-25 and task 52.1.)*
    - _Requirements: 27 (REQ-AUDIT-001..003)_ *(Reconciliation 2026-06-16: was "16.1 (REQ-AUDIT-001..003)" — 16.1 is the spine-smoke-test requirement (boilerplate phase tag copy-pasted across the Phase-2 migration block); the `gate_audit_log` table maps to Requirement 27 / REQ-AUDIT.)*

  - [ ]* 28.9 Write integration tests for Postgres schema
    - Run all 8 migrations (001–008) on a test Neon branch; assert all EIGHT tables created (`requirements`, `coverage_items`, `traceability_links`, `evidence_records`, `run_state`, `domain_baseline_checklists`, `requirement_versions`, `gate_audit_log`); test `evidence_complete` CHECK rejects incomplete records; assert `coverage_items.in_scope` defaults to true *(Reconciliation 2026-06-15: was "all 6 migrations / all tables"; now 8 tables / 8 migrations)*
    - `requirement_versions`-specific constraint assertions *(Reconciliation 2026-06-16: was generic "correct columns and constraints" only)*: assert `UNIQUE (requirement_id, version)` rejects a duplicate `(requirement_id, version)` insert; assert `created_at` is populated by `DEFAULT now()` when omitted; assert the `requirements(id)` FK rejects a row with a dangling `requirement_id`
    - _Requirements: 5.6, 16.1_

  - [ ] 28.10 Migration runner + `schema_migrations` bookkeeping + apply-on-deploy *(Reconciliation 2026-06-16: no runner, bookkeeping table, or real-DB apply step existed — the only application path was the test-branch integration tests 28.9/33.1.)*
    - Name a migration runner (default: `dbmate`; alternatives golang-migrate / sqitch / alembic) and a `schema_migrations` tracking table; apply order = file-name prefix `001`..`008`
    - Add a CI/deploy step that applies pending migrations to the target (non-test) Neon branch on merge/deploy — distinct from the test-branch application in 28.9
    - _Requirements: 16.1_

  - [ ] 28.11 Migration idempotency / re-run / rollback contract *(Reconciliation 2026-06-16: no idempotency/rollback text existed.)*
    - State the idempotency contract: one-time tracked apply via `schema_migrations` (28.10) OR `CREATE TABLE IF NOT EXISTS`; declare migrations forward-only (no DOWN/rollback files) unless a rollback file is explicitly provided
    - Document `gate_audit_log` (008) as create-once so a re-run does not error or duplicate the append-only log
    - _Requirements: 16.1_

- [ ] 29. Traceability link writer — commit trailer parser
  - [ ] 29.1 Write `tools/traceability_writer.py`
    - Implement `parse_commit_trailers(commit_sha: str) -> list[str]`: extract requirement IDs matching `[A-Z]+-[A-Z]+-[0-9]{3}` from `git log --format=%B -n1 {sha}` (import the shared `tools/req_id_scan.py` trailer-ID helper also used by `orphan_detector.py` (task 20.1) to prevent regex drift; `assert_commit_has_req_id` owns the REQ-6.2 commit-has-req-id gate, `orphan_detector` owns REQ-6.3 orphan detection) *(Reconciliation 2026-06-16)*
    - Implement `write_traceability_link(req_id, link_type, target_ref, direction)`: insert into `traceability_links` table
    - Implement `assert_commit_has_req_id(commit_sha)`: raise `TraceabilityError` if no requirement ID found in trailer
    - _Requirements: 6.1, 6.2_

  - [ ]* 29.2 Write property test for commit trailer requirement ID
    - **Property 10: Commit Trailer Requirement ID**
    - **Validates: Requirements 6.2**
    - Generate arbitrary commit message strings; assert `parse_commit_trailers` returns non-empty list only when at least one ID matching `[A-Z]+-[A-Z]+-[0-9]{3}` is present; assert commits without IDs raise `TraceabilityError`
    - `# Feature: spec-to-evidence-control, Property 10: Commit Trailer Requirement ID`

- [ ] 30. Evidence storage integration — `evidence_collector.py` → `evidence_records` table
  - [ ] 30.1 Extend `tools/evidence_collector.py` with Postgres persistence
    - Add `store_to_postgres(record: EvidenceRecord, req_id: str, commit_sha: str, actor_agent: str)`: insert into `evidence_records` table via `db_connection.get_connection()`; fall back to `feature_list.json` update if DB unavailable *(Reconciliation 2026-06-16: added the `actor_agent` parameter — assert it equals `verifier.md` and reject implementer-authored evidence at write time (Property 24, role separation). CRITICAL CONSTRAINT: do NOT add `actor_agent` to the EvidenceRecord JSON object — that schema is `additionalProperties: false` over exactly the four fields (`test_file`, `test_name`, `output_hash`, `collected_at`), so a fifth field would break Property 2/CHECK-7 and be rejected by the SubagentStop and PreToolUse status-guard validators. `actor_agent` lives only on the 7-column `evidence_records` Postgres row.)*
    - *(Reconciliation 2026-06-16, Note N-25 gate-consistency:)* when `db_connection.health_check()` fails, the `feature_list.json` fallback MUST reach the SAME allow/block decision as Postgres and NEVER fail-open, taking the more conservative (blocking) result on divergence; a fail-open or divergent collector fallback would silently weaken the OPA zero-evidence gate. Cite REQ-STORE-001/003 (Postgres single source of truth; reconstructable independently of any model session).
    - _Requirements: 16.2_

  - [ ]* 30.2 Write integration tests for evidence storage
    - Test: `store_to_postgres` with complete record → row appears in `evidence_records` with correct field values
    - Test: **Property 19 Phase-2 Postgres round-trip** — after `store_to_postgres`, the record is retrievable by `requirement_id` and `commit_sha` with all four fields intact *(Reconciliation 2026-06-16: this is the Postgres store/retrieve portion of Property 19 split out from the Phase-0 task 3.2; it validates Requirements 16.2.)*
    - Test: DB unavailable → falls back to `feature_list.json` without raising AND reaches the same conservative/blocking decision (Note N-25; never fail-open)
    - _Requirements: 16.2_

- [ ] 31. Run state persistence — `run_state` table integration
  - [ ] 31.1 Write `tools/run_state_manager.py`
    - Implement `load_run_state(session_id) -> RunState`: read from `run_state` table; fall back to `claude-progress.txt` if DB unavailable
    - Implement `save_run_state(run_state: RunState)`: upsert into `run_state` table; also write `claude-progress.txt` as file-backed duplicate — the duplicate MUST include `resume_integrity_ok` and the baseline `state_hash` (not only `status`/`no_progress_n`/`stop_hook_active`), so the PreToolUse integrity guard (task 49.1) has a file-backed source and reaches the SAME conservative/blocking decision on DB-down (never fail-open) *(Reconciliation 2026-06-16, Note N-25: `resume_integrity_ok` lives only in `run_state` (Postgres); without persisting it + `state_hash` to `claude-progress.txt` the integrity guard's fallback decision is undefined and risks fail-open.)*
    - Wire `load_run_state` / `save_run_state` into `stop_hook.py` replacing current file-only reads
    - _Requirements: 11.1_

  - [ ] 31.2 Write the run_state POPULATOR — per-turn counter advancement (**D3 loop-driver**, distinct from 31.1 persistence) *(Reconciliation 2026-06-18: the steering audit's D3 prereq — remediation §7.2 item 2: A2/A4 CONSUME block_streak/external_blocker/iteration_count/no_progress_n but 'Nothing populates them.' 31.1 only load/save-persists a RunState; it never advances the counters, so the cap/HANDOFF/escalation paths are inert with counters stuck at 0.)*
    - Implement `advance_turn(run_state, turn_outcome) -> RunState`: increment `iteration_count` once per implementation turn; on a Stop/SubagentStop block of the SAME unresolved condition increment `block_streak`, else reset it to 0; set/clear `external_blocker` from the turn's blocker classification; on any progress (an `unproven→proven` flip OR a new commit) reset `no_progress_n` to 0 else advance it (the existing `check_no_progress` window). The populator is the SOLE writer of these counters; the Stop/SubagentStop hooks READ them.
    - Call the populator from the loop driver each turn BEFORE the Stop hook evaluates, persisting via `save_run_state` (31.1) so the durable + file-backed run_state the gates read is current.
    - Unit test: a 3-turn block-streak on one condition reaches the escalation rung; a cleared blocker resets `block_streak`; a progress turn resets `no_progress_n`.
    - _Requirements: 14.1, 14.2, REQ-LOOP-005_

- [ ] 32. SLSA provenance — `actions/attest-build-provenance`
  - [ ] 32.1 Create `.github/workflows/release.yml`
    - Trigger on `push` to `main` (or tag)
    - After build: call `actions/attest-build-provenance@v1` to sign artifact
    - Document `gh attestation verify` command in `docs/slsa-verification.md`
    - _Requirements: 17.3_

- [ ] 33. Phase 2 durable-state integration test
  - [ ] 33.1 Write `tests/integration/test_phase2_integration.py`
    - Against a test Neon branch: run all 8 migrations (001–008); assert all EIGHT tables exist (`requirements`, `coverage_items`, `traceability_links`, `evidence_records`, `run_state`, `domain_baseline_checklists`, `requirement_versions`, `gate_audit_log`) with correct columns and constraints *(Reconciliation 2026-06-15: was "all 6 migrations")*
    - Insert a requirement record; insert a coverage item with `status='unproven'`; assert `evidence_complete` CHECK rejects an `evidence_records` row with empty `output_hash`
    - Insert a complete evidence record; assert it is retrievable by `requirement_id` and `commit_sha` with all four fields intact
    - `requirement_versions`-specific constraint assertions *(Reconciliation 2026-06-16: was covered only by the generic "correct columns and constraints" above)*: assert `UNIQUE (requirement_id, version)` rejects a duplicate `(requirement_id, version)` insert; assert `created_at` is populated by `DEFAULT now()` when omitted; assert the `requirements(id)` FK rejects a row with a dangling `requirement_id`
    - Write a commit message containing a requirement ID; run `parse_commit_trailers`; assert the ID is returned
    - Write a commit message with no requirement ID; run `assert_commit_has_req_id`; assert `TraceabilityError` is raised
    - Call `load_run_state` with the DB unavailable; assert fallback reads from `claude-progress.txt` without raising
    - _Requirements: 6.1, 6.2, 6.3, 11.1, 16.1, 16.2, 16.3_ *(Reconciliation 2026-06-16: 6.3 here covers the `parse_commit_trailers`/`assert_commit_has_req_id` commit-trailer leg; the orphan-detection 6.3 assertion is owned by task 26.1, which actually invokes `orphan_detector.py`.)*

---

### Phase 3 — Observability

- [ ] 34. OTel setup and OTLP exporter configuration
  - [ ] 34.1 Write `tools/telemetry.py`
    - Configure `CLAUDE_CODE_ENABLE_TELEMETRY=1` and `OTEL_SEMCONV_STABILITY_OPT_IN=gen_ai_latest_experimental` in `.env.example` and CI workflow env
    - Implement `init_tracer(service_name: str)`: create `TracerProvider` with `OTLPSpanExporter` reading `OTLP_ENDPOINT` from environment; set export interval DEFAULT ≤5 seconds
    - Implement `get_tracer() -> Tracer`: return named tracer for `spec-to-evidence-control`
    - Pin OTel SDK version in `requirements.txt`
    - _Requirements: 12.1, 12.2_

  - [ ]* 34.2 Write unit tests for OTel setup
    - Test: `init_tracer` with missing `OTLP_ENDPOINT` → raises `ConfigError`
    - Test: tracer emits spans to mock OTLP exporter; assert export interval ≤5 seconds
    - _Requirements: 12.2_

- [ ] 35. W3C Baggage `BaggageSpanProcessor` for `requirement.id` propagation
  - [ ] 35.1 Implement `BaggageSpanProcessor` in `tools/telemetry.py`
    - Write `RequirementBaggageProcessor(SpanProcessor)`: on `on_start`, read active `requirement.id` from context; set `baggage.set_baggage("requirement.id", req_id)` on span; assert `requirement.id` is non-empty for any span with an active requirement
    - Register processor in `init_tracer()`
    - _Requirements: 6.4, 12.4_

  - [ ]* 35.2 Write property test for W3C Baggage requirement ID propagation
    - **Property 12: W3C Baggage Requirement ID Propagation**
    - **Validates: Requirements 6.4, 12.4**
    - Generate arbitrary spans under an active requirement context; assert every span's Baggage contains `requirement.id` with non-empty value; assert no requirement-processing span is emitted without this entry
    - `# Feature: spec-to-evidence-control, Property 12: W3C Baggage Requirement ID Propagation`

- [ ] 36. Hook decision event forwarding to OTLP
  - [ ] 36.1 Extend all six hooks (Stop, PreToolUse, PostToolUse, SubagentStop, SessionStart, PreCompact) to emit OTel gate-decision events *(Reconciliation 2026-06-15: was "all five hooks"; there are 6)*
    - In each hook's decision return path, call `telemetry.get_tracer().start_as_current_span(...)` and set attributes appropriate to the hook's class *(Reconciliation 2026-06-16: REQ-OBS-003 / criterion 12.3 is scoped to "WHEN a hook makes a gate decision" — a uniform allow/block `decision` attribute on a single `hook.decision` span is degenerate for the hooks that never gate. Specify the attribute set per hook class:)*
      - **Gate-making hooks** (Stop, PreToolUse, SubagentStop) — emit `span name "hook.decision"` with `hook.event`, `tool.name`, `decision` (allow/block), `reason`, `requirement.id`. These are the true gate decisions REQ-OBS-003 forwards. *(Reconciliation 2026-06-16: also set `actor_agent` so the live OTel span and the durable `gate_audit_log` row (REQ-AUDIT-001, which records `actor_agent` in the audit tuple) carry the same per-agent attribution.)*
      - **PostToolUse** (non-gating; always exits 1, never allow/block) — emit a distinct `span name "hook.feedback"` with `hook.event`, `tool.name`, `findings_count` (+ severity breakdown); do NOT reuse the allow/block `decision` attribute. PostToolUse forwards informational feedback telemetry, not an audit-logged gate decision.
      - **SessionStart, PreCompact** (non-gating; always exit 0, no allow/block) — emit a distinct informational span (e.g. `"hook.session_start"` / `"hook.checkpoint"` with item-count attributes; `decision="n/a"`); either omit `requirement.id` or, for SessionStart, list both ids explicitly (REQ-STATE-003 and REQ-STATE-005) — do NOT emit a gate-decision allow/block attribute so the trace schema reflects which hooks actually gate.
    - Emit via the same OTLP endpoint as agent spans
    - _Requirements: 12.3_

- [ ] 37. Langfuse backend connection
  - [ ] 37.1 Configure Langfuse as the default OTLP backend
    - Set `OTLP_ENDPOINT` in `tools/telemetry.py` to read from environment variable `OTLP_ENDPOINT` (no hardcoded URLs)
    - Add `OTLP_ENDPOINT=https://cloud.langfuse.com/api/public/otel/v1/traces` as a commented example in `.env.example`
    - Add `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` to `.env.example` as required Langfuse auth variables
    - Write a `docs/observability-backends.md` file listing: Langfuse (MIT core, recommended default), SigNoz (MIT Expat core), Arize Phoenix (Elastic License 2.0 — source-available, NOT OSI, no hosted-service offering permitted) with the specific license note so backend choice is compliance-aware
    - _Requirements: 12.2, 12.5_

  - [ ]* 37.2 Write integration test for OTel export
    - Stand up a local OTLP collector (e.g., `opentelemetry-collector` via Docker); point `OTLP_ENDPOINT` at it
    - Call `init_tracer()` and emit one span with `requirement.id` Baggage; assert the collector receives the span and the Baggage attribute is present
    - _Requirements: 12.1, 12.4_

- [ ] 38. Phase 3 observability integration test
  - [ ] 38.1 Write `tests/integration/test_phase3_integration.py`
    - Call `init_tracer("spec-to-evidence-control")`; start a span under a mock `requirement.id` context; assert `RequirementBaggageProcessor` sets `requirement.id` on the span's Baggage
    - Simulate a `Stop` hook gate-decision (block); assert the hook emits a span with attributes `hook.event=Stop`, `decision=block`, `requirement.id` matching the active requirement
    - Assert that two gate evaluations with identical `feature_list.json` state but different mock prediction values produce the same span `decision` attribute value
    - Assert all hook spans are exported to the same OTLP endpoint as agent spans (verify via shared `TracerProvider`)
    - _Requirements: 12.3, 12.4, 13.6_

---

### Phase 4 — Property-Based Tests (Full Suite)

- [ ] 39. Complete PBT suite — all 32 correctness properties *(Reconciliation 2026-06-16: canonical count is 32 — Properties 1–24 plus 25–32. Properties 25–29 are authored under tasks 48–52 (subtasks 39.15–39.19 below); Property 30 (omission-declaration gate, CHECK-13a/13b) under task 54 (subtask 39.20); Property 31 (perf/a11y/ui-screen evidence, REQ-VERIFY-007/008) under task 51 (subtask 39.21); Property 32 (CI secrets diff-scan blocks merge, REQ-17.2) under task 45 (subtask 39.22). Properties 31–32 are PBT/CI-verified with no Z3 oracle; the harness self-count stays 34.)*
  - [ ] 39.1 Write `tests/property/test_coverage_model.py`
    - Property 1: Coverage Item Schema Invariant (`test_coverage_item_schema_invariant`)
    - Property 2: Evidence Schema Enforcement (`test_evidence_schema_enforcement`)
    - Property 3: Identity-Mutation Blockade (`test_identity_mutation_blockade`)
    - Property 4: Completion Gate — Prediction Independence (`test_completion_gate_prediction_independence`)
    - Each test: `@settings(max_examples=100)`, tag comment `# Feature: spec-to-evidence-control, Property N: <text>`
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 10.1, 13.6, 19.2_

  - [ ]* 39.2 Write property test for completion gate prediction independence
    - **Property 4: Completion Gate — Prediction Independence**
    - **Validates: Requirements 10.1, 13.6, 19.2**
    - Generate pairs of `(coverage_state, prediction_A, prediction_B)` where `prediction_A ≠ prediction_B` but coverage state is identical; assert gate decision is identical for both; assert no prediction variable appears in gate logic
    - `# Feature: spec-to-evidence-control, Property 4: Completion Gate — Prediction Independence`

  - [ ] 39.3 Write `tests/property/test_hooks.py`
    - Property 5: Stop Hook — Unproven Blocks Termination (`test_stop_hook_unproven_blocks`)
    - Property 6: Plan Approval Gate (`test_plan_approval_gate`)
    - Property 7: Scope Sequencing Gate (`test_scope_sequencing_gate`)
    - Property 8: No-Progress → HANDOFF Only (`test_no_progress_handoff`)
    - Property 9: Cap and Budget → HANDOFF Only (`test_cap_budget_handoff`)
    - Property 21: Hook Exit-Code Contract (`test_hook_exit_code_contract`)
    - _Requirements: 5.5, 7.4, 7.5, 10.2, 13.5, 14.1, 14.2, 18.1_

  - [ ]* 39.4 Write property test for hook exit-code contract
    - **Property 21: Hook Exit-Code Contract**
    - **Validates: Requirements 13.5**
    - Generate hook invocation scenarios with exit codes 0, 1, 2, and arbitrary non-zero; assert exit 0 → tool proceeds; exit 2 → tool blocked + stderr fed to agent; exit 1 → NOT blocked; other non-zero → non-blocking
    - *(Reconciliation 2026-06-16: include an explicit SubagentStop case so its exit-code conformance is not merely transitive — assert SubagentStop's allow (exit 0) / block (exit 2 with stderr) / fail-closed-on-exception (exit 2) behavior conforms to REQ-STEER-005 (13.5). The exit-code contract is the foundation of this hook's entire allow/block behavior.)*
    - `# Feature: spec-to-evidence-control, Property 21: Hook Exit-Code Contract`

  - [ ] 39.5 Write `tests/property/test_spec_validator.py`
    - Property 14: Spec Validator Returns Structured Output (`test_spec_validator_structured_output`)
    - Property 15: Spec-Completion Convergence Gate (`test_spec_completion_convergence`)
    - Property 16: EARS Pattern Assignment Uniqueness (`test_ears_pattern_uniqueness`)
    - Property 17: Vague-Adjective Rejection (`test_vague_adjective_rejection`)
    - _Requirements: 1.2, 1.4, 4.1, 4.3_

  - [ ]* 39.6 Write property test for spec-completion convergence gate
    - **Property 15: Spec-Completion Convergence Gate**
    - **Validates: Requirements 4.3**
    - Generate sequences of `violation_count` values across consecutive passes; assert system routes to HANDOFF whenever count does not strictly decrease between any two consecutive passes; assert continuation only on strict decrease
    - `# Feature: spec-to-evidence-control, Property 15: Spec-Completion Convergence Gate`

  - [ ] 39.7 Write `tests/property/test_traceability.py`
    - Property 10: Commit Trailer Requirement ID (`test_commit_trailer_req_id`)
    - Property 11: Orphan Detection (`test_orphan_detection`)
    - Property 12: W3C Baggage Requirement ID Propagation (`test_w3c_baggage_propagation`)
    - Property 13: UNMAPPED Blocks Advancement (`test_unmapped_blocks_advancement`)
    - Property 18: Checklist Version Link Fidelity (`test_checklist_version_link_fidelity`)
    - _Requirements: 2.2, 3.3, 6.2, 6.3, 6.4, 12.4_

  - [ ]* 39.8 Write property test for UNMAPPED blocks advancement
    - **Property 13: UNMAPPED Blocks Advancement**
    - **Validates: Requirements 2.2**
    - Generate domain-baseline checklist states with arbitrary items marked UNMAPPED; assert implementation-phase advancement is blocked whenever any item is UNMAPPED; assert unblocking requires the item to be covered by a mapped requirement
    - `# Feature: spec-to-evidence-control, Property 13: UNMAPPED Blocks Advancement`

  - [ ]* 39.9 Write property test for checklist version link fidelity
    - **Property 18: Checklist Version Link Fidelity**
    - **Validates: Requirements 3.3**
    - Generate checklist use events with arbitrary path/version/sha triples; assert the `checklist_ref` recorded in `feature_list.json` matches the actual git blob SHA at time of use; assert any mismatch causes validation failure
    - *(Reconciliation 2026-06-16: the property test alone has no deterministic SHA oracle. Add a CI/task step — extend this subtask or the coverage-gate workflow — that runs `git hash-object <checklist_ref.path>` and fails if the result does not equal `feature_list.json`'s recorded `checklist_ref.sha`, wiring Property 18 to an actual git-blob-SHA fidelity check rather than a generated-only assertion.)*
    - `# Feature: spec-to-evidence-control, Property 18: Checklist Version Link Fidelity`

  - [ ] 39.10 Write `tests/property/test_evidence.py`
    - Property 2: Evidence Schema Enforcement (if not already covered)
    - Property 19: Evidence Round-Trip (`test_evidence_round_trip`)
    - Property 20: Secret-Free Prompts, Spans, and URLs (`test_secret_free_output`)
    - Property 23: Line Coverage Threshold on Touched Files (`test_line_coverage_threshold`)
    - Property 24: Subagent Role Separation (`test_subagent_role_separation`)
    - _Requirements: 5.3, 5.6, 9.2, 9.6, 16.2, 17.5_

  - [ ]* 39.11 Write property test for secret-free prompts, spans, and URLs
    - **Property 20: Secret-Free Prompts, Spans, and URLs**
    - **Validates: Requirements 17.5**
    - Generate arbitrary prompt texts, span attribute dicts, and URLs; assert none matching known secret patterns (regex for API keys, tokens, passwords, connection strings) are emitted; assert any matching pattern is rejected before emission
    - `# Feature: spec-to-evidence-control, Property 20: Secret-Free Prompts, Spans, and URLs`

  - [ ]* 39.12 Write property test for line coverage threshold
    - **Property 23: Line Coverage Threshold on Touched Files**
    - **Validates: Requirements 9.6**
    - Generate slice results with arbitrary per-file coverage percentages; assert Verifier marks slice failed and does not emit `proven` status whenever any touched file has coverage < 85%; assert `proven` emitted only when all files ≥ 85%
    - `# Feature: spec-to-evidence-control, Property 23: Line Coverage Threshold on Touched Files`

  - [ ]* 39.13 Write property test for subagent role separation
    - **Property 24: Subagent Role Separation (Implementer Cannot Self-Verify)**
    - **Validates: Requirements 9.2**
    - Generate evidence chains with arbitrary `actor_agent` identities; assert any Evidence_Record where `actor_agent == "implementer.md"` is rejected; assert only evidence from `verifier.md` is accepted *(Reconciliation 2026-06-16: renamed `acting_agent`→`actor_agent` — canonical field name everywhere per design.md; `actor_agent` is a column on the 7-column evidence_records Postgres row, NOT a field on the 4-field EvidenceRecord JSON object, which is `additionalProperties: false`.)*
    - `# Feature: spec-to-evidence-control, Property 24: Subagent Role Separation`

  - [ ] 39.14 Write `tests/property/test_completion_gate.py`
    - Property 4: Completion Gate — Prediction Independence
    - Property 5: Stop Hook — Unproven Blocks Termination
    - Property 22: OPA Zero-Evidence Policy at Merge
    - _Requirements: 10.1, 10.2, 10.3, 13.6, 19.2_

  - [ ]* 39.15 Write `tests/property/test_amendment.py` — **Property 25: Amendment Monotonicity (CHECK-10a/10b)**
    - Authored alongside task 48 (requirement-amendment versioning). Generate amendment events on `proven` items; assert each amended item re-enters `unproven` and COMPLETE is blocked while any amended item is un-reproven; assert monotonic re-proof. Maps to Z3 CHECK-10a/10b.
    - `# Feature: spec-to-evidence-control, Property 25: Amendment Monotonicity`
    - _Requirements: 22 (REQ-COV-007)_ *(Reconciliation 2026-06-16: was "5.2 (REQ-COV-007)" — Req 5 is the coverage model; the REQ-COV-007 amendment obligation is Requirement 22.)*

  - [ ]* 39.16 Write `tests/property/test_state_integrity.py` — **Property 26: Resumed-State Integrity (CHECK-11a/11b)**
    - Authored alongside task 49 (resumed-state integrity). Generate resumed sessions with matching and mismatched state hashes; assert `run_state.resume_integrity_ok` is true only on match and that the PreToolUse integrity guard blocks (exit 2) the first write when it is false. Maps to Z3 CHECK-11a/11b.
    - `# Feature: spec-to-evidence-control, Property 26: Resumed-State Integrity`
    - _Requirements: REQ-STATE-005_

  - [ ]* 39.17 Write `tests/property/test_checklist_approval.py` — **Property 27: Checklist-Approval-Before-Use (CHECK-12)**
    - Authored alongside task 50. Generate checklist states with arbitrary `approved_at` values; assert any DRAFT (unapproved) checklist cannot be used by the Initializer; assert use is permitted only after human approval. Maps to Z3 CHECK-12.
    - `# Feature: spec-to-evidence-control, Property 27: Checklist-Approval-Before-Use`
    - _Requirements: 24.1 (REQ-SPEC-016); 3.1, 3.3 (sourcing context)_ *(Reconciliation 2026-06-16: REQ-SPEC-016 is Requirement 24.1, not Requirement 3's sourcing criteria; 3.1/3.3 retained as sourcing context.)*

  - [ ]* 39.18 Write `tests/property/test_audit_verify.py` — **Property 28: Audit-Log Tamper Detection (REQ-AUDIT-001, REQ-AUDIT-002)** *(Reconciliation 2026-06-16: renamed from `test_audit_log.py` — the assertion exercises `tools/audit_verify.py` (the VERIFIER), not the producer; the producer's own write-side unit tests live in task 52.4. If a producer-side property test is later wanted it gets its own `test_audit_log.py`.)*
    - Authored alongside task 52. Generate hash-chained `gate_audit_log` sequences and inject arbitrary mutations; assert `tools/audit_verify.py` fails on any broken link and passes only on an intact chain (genesis `prev_hash = sha256("")`). Maps to REQ-AUDIT-002.
    - *(Reconciliation 2026-06-16, POSITIVE intact-chain producer-contract reproduction — REQ-AUDIT-001 / Req 27.5:)* also assert the verifier reproduces the exact producer contract on an intact chain: genesis `prev_hash = sha256("")`; the canonical field-set and ordering `(seq, event_name, tool_name, decision, reason, requirement_id, actor_agent, created_at)`; and that `seq` and `created_at` ARE included in `entry_hash`. Without this the verifier's reproduction of the REQ-AUDIT-001/27.5 producer contract is untested.
    - `# Feature: spec-to-evidence-control, Property 28: Audit-Log Tamper Detection`
    - _Requirements: REQ-AUDIT-001, REQ-AUDIT-002_

  - [ ]* 39.19 Write `tests/property/test_research_claims.py` — **Property 29: Research-Claim Authority Labeling + Fact-Check (REQ-SPEC-017)**
    - Authored alongside task 50. Generate Research_Sub_Agent claims with arbitrary source/authority/fact-check combinations; assert any claim lacking a source URL, authority-tier label, or independent fact-check is rejected before human review. Maps to REQ-SPEC-017.
    - `# Feature: spec-to-evidence-control, Property 29: Research-Claim Authority Labeling`
    - _Requirements: 24.2 (REQ-SPEC-017); 3.1, 3.3 (sourcing context)_ *(Reconciliation 2026-06-16: REQ-SPEC-017 is Requirement 24.2, not Requirement 3's sourcing criteria; 3.1/3.3 retained as sourcing context.)*

  - [ ]* 39.20 Write `tests/property/test_omission.py` — **Property 30: Omission-Declaration Gate (REQ-SPEC-018, CHECK-13a/13b)** *(Reconciliation 2026-06-16: task 54 referenced a "Property 30 test in subtask" that did not exist — the PBT block 39.15–39.19 covered Properties 25–29 only; this subtask gives Property 30 its concrete test home.)*
    - Authored alongside task 54. Generate subagent outputs with arbitrary `omission_declaration` values; assert any result whose `omission_declaration` is null or absent is rejected (exit 2) by the `subagent_stop_hook.py` omission-declaration guard, and that a present, non-null declaration is accepted. Maps to Z3 CHECK-13a/13b.
    - `# Feature: spec-to-evidence-control, Property 30: Omission-Declaration Gate`
    - _Requirements: REQ-SPEC-018_
  - [ ]* 39.21 Write `tests/property/test_perf_a11y.py` — **Property 31: Perf / A11y / UI-Screen Evidence Required (REQ-VERIFY-007/008)** *(Reconciliation 2026-06-16: new — pins Property 31; authored alongside task 51's `perf_a11y_verifier` capability. No Z3 oracle; PBT-verified; harness self-count stays 34.)*
    - For an NFR item of `subtype` `performance`/`accessibility` marked `proven`, assert a perf/a11y Evidence_Record (`evidence_kind` `perf`/`a11y`) is attached; for a `subtype=='ui-screen'` item assert every `declared_states` entry (≥ `empty`/`loading`/`error`/`ready`) has a Playwright render-assertion Evidence_Record; assert the item cannot be `proven` without it.
    - `# Feature: spec-to-evidence-control, Property 31: Perf / A11y / UI-Screen Evidence Required`
    - _Requirements: REQ-VERIFY-007/008_
  - [ ]* 39.22 Write `tests/property/test_secrets_scan.py` — **Property 32: CI Secrets Diff-Scan Blocks Merge (REQ-17.2 / REQ-SEC-002)** *(Reconciliation 2026-06-16: new — pins Property 32; fixture test against `secrets-scan.yml` (tasks 45 / 40.2). No Z3 oracle; CI/fixture-verified; harness self-count stays 34. Distinct from Property 20, the commit-side gate.)*
    - Fixture test: a PR diff containing a planted secret (API key / token / password / connection string) FAILS the `secrets-scan` check and BLOCKS merge; a clean diff PASSES. This is the merge-side half of "block the commit or merge"; the commit-side half is Property 20 (REQ-17.5).
    - `# Feature: spec-to-evidence-control, Property 32: CI Secrets Diff-Scan Blocks Merge`
    - _Requirements: REQ-17.2 (REQ-SEC-002)_

- [ ] 40. Integrate `formal_verification_merged.py` as required CI check (Phase 4 hardening)
  - [ ] 40.1 Update `.github/workflows/formal-verification.yml`
    - Add `hypothesis` PBT run step: `python -m pytest tests/property/ -v`
    - Gate PR merge on this workflow in the GitHub repository ruleset
    - _Requirements: 4.1_

  - [ ] 40.2 Create `.github/workflows/secrets-scan.yml` and register `secrets-scan` as a REQUIRED status check *(Reconciliation 2026-06-15: wires task 45 into CI)*
    - Trigger on `pull_request` (scan the PR diff) *(Reconciliation 2026-06-16: secrets-scan was the sole sibling required-check workflow with no explicit `on:` trigger stated; added to match the codeql/coverage-gate/formal-verification/property-tests convention.)*
    - Run `gitleaks` (or `trufflehog`) on the PR diff; fail (block merge) on any detected secret
    - Add a fixture/acceptance test (e.g. in `tests/integration/test_github_actions.py`): a fixture PR diff containing a fake AWS key → workflow fails (merge blocked); a clean diff → workflow passes — this is the component's "done" definition *(Reconciliation 2026-06-16: no acceptance/fixture test was specified for this component anywhere; the Phase-0 spine "Test to pass" column has no secrets-scan row since it is Phase 1.)*
    - Add the workflow to the GitHub repository ruleset as a required check (the canonical required-checks list is task 14.2 — reference it, do not re-list); document in `docs/github-ruleset.md`
    - *(Reconciliation 2026-06-16, phase alignment:)* secrets-scan.yml is a **Phase 1** verification-depth gate (co-located conceptually with codeql.yml task 23 / Semgrep task 24); the design inventory Phase label, task 40.2, and task 45 SHALL all carry the same Phase 1 label. *(Reconciliation 2026-06-16, build-order note: same `wave-33` early-registration caveat as 40.3 below applies — task 45 (the gitleaks step) need not pre-exist the workflow file, but `fail_action`/required-check ENFORCEMENT should not block merges until task 45's scan logic lands.)*
    - _Requirements: 17.2_

  - [ ] 40.3 Create `.github/workflows/audit-chain-verify.yml` and register `audit-chain-verify` as a REQUIRED status check *(Reconciliation 2026-06-15: wires task 52 into CI; verification trigger = required CI status check at merge PLUS on-demand via `audit_verify.py`)*
    - *(Reconciliation 2026-06-16, build-order inversion fix:)* the dependency graph schedules this subtask at wave id 33, NINE waves before wave id 42 builds `tools/audit_verify.py` (task 52.2) and its producer wiring (52.3). To avoid a REQUIRED check invoking a tool that does not yet exist, SPLIT this subtask: the **workflow file** may be created early (wave 33), but its **required-check registration / merge-blocking enforcement MUST be gated until after task 52.2 (and the producer 52.3) land** — do not mark `audit-chain-verify` a blocking required check before `tools/audit_verify.py` exists. (Alternatively move the registration leg into a wave at/after wave 42.) The same class of inversion exists for 40.2/secrets-scan vs task 45 — apply the same split there.
    - Run `python3 tools/audit_verify.py` to recompute the hash chain over `gate_audit_log`; fail (block merge) on any broken link
    - Add the workflow to the GitHub repository ruleset as a required check (the canonical required-checks list is task 14.2 — reference it, do not re-list); document in `docs/github-ruleset.md`
    - _Requirements: REQ-AUDIT-001..003_ *(Reconciliation 2026-06-16: dropped the stray `12.x` prefix and REQ-OBS-006 — `12.x` is not a valid requirement id and REQ-OBS-006 is the reasoning-loop detector (Requirement 26), which this audit-chain CI gate does not enforce; it only recomputes the hash chain over `gate_audit_log`. The parent task 52 legitimately bundles both concerns; this CI gate carries only the audit requirement.)*

  - [ ] 40.4 Create `.github/workflows/traceability-gate.yml` and register `traceability-gate` as a REQUIRED status check *(Reconciliation 2026-06-16: wires the previously-unwired `orphan_detector.py` (task 20.1) blocking gate for REQ-6.3 "block the run" — its non-zero exit was previously consumed only by test task 26.1; this is the production mechanism that blocks the merge.)*
    - Run `python3 tools/orphan_detector.py` (full-repo scope); fail (block merge / non-zero exit) when any orphan is found — the exit-code-to-block contract is: the CI required check fails the merge (equivalently a PreToolUse exit-2 gate in-session)
    - Fold in the REQ-6.2 commit-trailer enforcer: invoke `tools/traceability_writer.py::assert_commit_has_req_id` over the PR's commits (it raises `TraceabilityError` → non-zero exit) so a single shared commit-trailer gate satisfies BOTH REQ-6.2 (commit has ≥1 requirement ID) and REQ-6.3's trailer obligation *(Reconciliation 2026-06-16: `assert_commit_has_req_id` previously had no stated caller/hook/CI gate)*
    - Add the workflow to the GitHub repository ruleset as a required check; document in `docs/github-ruleset.md`
    - _Requirements: 6.2, 6.3_

  - [ ] 40.5 Register `zap-baseline` as a REQUIRED status check (Phase-4 ruleset registration for task 56's workflow) *(Reconciliation 2026-06-16: required-status-check registration is a Phase-4 task-40 activity; the Phase-2 build task 56 creates `.github/workflows/zap-baseline.yml` but cannot itself register a Phase-4 ruleset gate, leaving REQ-SEC-008.2 unscheduled in every phase. 40.4 is already traceability-gate, so this lands as 40.5.)* — add `.github/workflows/zap-baseline.yml` (created in task 56, `zaproxy/action-baseline@v0.12.0`, `fail_action: true`, `on: pull_request`) to the GitHub repository ruleset as a required check (canonical list = task 14.2); document in `docs/github-ruleset.md`. Add `40.5` to dependency-graph wave id 33. _Requirements: REQ-SEC-008 (31.2)_
  - [ ] 40.6 Register `deepeval-gate` as a REQUIRED status check (Phase-4 ruleset registration for task 55/55.1's workflow) *(Reconciliation 2026-06-16: parallel to 40.5 — the Phase-2 build task 55 cannot register a Phase-4 ruleset gate, leaving REQ-EVAL-001.3 unscheduled.)* — add `.github/workflows/deepeval-gate.yml` (created in task 55.1) to the GitHub repository ruleset as a required check (canonical list = task 14.2); document in `docs/github-ruleset.md`. Add `40.6` to dependency-graph wave id 33. _Requirements: REQ-EVAL-001 (REQ-EVAL-001.3)_

- [ ] 41. PBT CI workflow — run on every PR
  - [ ] 41.1 Create `.github/workflows/property-tests.yml`
    - Trigger on every `pull_request`
    - Install all test dependencies; run `python -m pytest tests/property/ --hypothesis-seed=0 -v`
    - Upload `hypothesis/` database as artifact for reproducibility
    - Register as required status check in GitHub repository ruleset
    - _Requirements: 4.1, 9.1_

- [ ] 42. Final PBT CI run and gate registration
  - [ ] 42.1 Run the full property-based test suite locally and fix any failures
    - Execute `python -m pytest tests/property/ --hypothesis-seed=0 -v` and resolve any property failures
    - For each failing property: identify the invariant violation, trace it to the relevant requirement, fix the implementation (not the test)
    - Confirm all 32 properties pass with `--hypothesis-seed=0` (deterministic seed for CI reproducibility) *(Reconciliation 2026-06-16: includes Properties 25–29 (amendment monotonicity, resumed-state integrity, checklist-approval-before-use, audit-log tamper detection, research-claim authority labeling — tasks 48–52); Property 30 (omission-declaration gate — task 54); Property 31 (perf/a11y/ui-screen evidence — task 51); Property 32 (CI secrets diff-scan blocks merge — task 45))*
    - _Requirements: 1.2, 1.4, 2.2, 3.3, 4.1, 4.3, 5.1, 5.2, 5.3, 5.5, 5.6, 6.2, 6.3, 6.4, 7.4, 7.5, 8.1, 9.2, 9.6, 10.1, 10.2, 10.3, 13.5, 13.6, 14.1, 14.2, 16.2, 17.5, 19.2_

---

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- The hard phasing constraint is absolute: every Phase 0 task (1–17) must be complete before any Phase 1 task (18–26) begins
- Each task references specific requirements for traceability
- All hook implementations must use `"type": "command"` — never HTTP or MCP — to ensure fail-closed behavior
- The `stop_hook_active` reentrancy guard is critical to prevent cascade blocking; implement it in task 5 before testing
- Postgres is the durable source of truth (Phase 2), but all Phase 0–1 gates must work correctly with file-only fallback
- *(Reconciliation 2026-06-15, N-25 — Postgres-unavailable fallback gate-consistency):* when `db_connection.health_check()` fails, every gate (Stop coverage gate, PreToolUse status/integrity guards, OPA merge policy) MUST fall back to the file-backed state (`feature_list.json` + `claude-progress.txt`) and reach the SAME allow/block decision it would on Postgres — never fail-open. The DB and file states are kept as duplicates (see tasks 30.1, 31.1); on divergence the gate takes the more conservative (blocking) result. The `gate_audit_log` producer (task 52.1) appends to the file-backed log when the DB is unavailable and reconciles on reconnect. *(Reconciliation 2026-06-16: this rule also governs the SessionStart WRITE side. If Postgres is down at SessionStart (health_check fails), the hook records `resume_integrity_ok` (and the baseline `state_hash`) to the file-backed `run_state` duplicate in `claude-progress.txt` rather than skipping the write, and reconciles to Postgres on reconnect — so the downstream PreToolUse integrity guard, which reads `resume_integrity_ok`, always has a file-backed source and keeps the conservative/blocking behavior. See task 49.2 (write) and task 31.1 (save_run_state must persist `resume_integrity_ok` + `state_hash` to the file duplicate).)*
- *(Reconciliation 2026-06-16, research-gate phase-ordering:)* `research.md` (task 10.4) is BUILT in Phase-0 wave 9 but its epistemic-integrity gate (task 50, REQ-SPEC-016/017), omission-declaration gate (task 54, REQ-SPEC-018), and checklist-approval tests (39.17/39.19) land in Phase 3+. The research agent MUST NOT be INVOKED on an un-gated product class until tasks 50/54 land — i.e. during Phase 0–2 it may be authored but its research-invocation/DRAFT-checklist path is gated by 50/54, so no un-gated DRAFT checklist or unlabeled/unfact-checked claim can drive discovery. This Phase-0-build / Phase-3-gate deferral is intentional.
- Property tests use `hypothesis` with `@settings(max_examples=100)` and the tag comment `# Feature: spec-to-evidence-control, Property N: <text>`
- The 32 correctness properties in Phase 4 are seeded throughout earlier phases (2, 3, 4, 5, 6, 8, 11) — the Phase 4 task consolidates and completes the full suite (Properties 1–24 from the original phases; Properties 25–32 under tasks 48–52, 54, 51, 45 — Properties 25–29 under tasks 48–52, Property 30 (omission-declaration gate) under task 54, Property 31 (perf/a11y/ui-screen evidence) under task 51, Property 32 (CI secrets diff-scan) under task 45) *(Reconciliation 2026-06-16: canonical count is 32 — added Property 31 (REQ-VERIFY-007/008) and Property 32 (REQ-17.2); both PBT/CI-verified, harness self-count stays 34.)*

---

## Task Dependency Graph

```json
{
  "waves": [
    {
      "id": 0,
      "tasks": ["1"]
    },
    {
      "id": 1,
      "tasks": ["1.1", "2.1", "12.1"]
    },
    {
      "id": 2,
      "tasks": ["2.2", "2.3", "3.1", "12.2"]
    },
    {
      "id": 3,
      "tasks": ["3.2", "3.3", "4.1"]
    },
    {
      "id": 4,
      "tasks": ["4.2", "4.3", "4.4", "4.5", "5.1"]
    },
    {
      "id": 5,
      "tasks": ["5.2", "5.3", "5.4", "5.5", "6.1"]
    },
    {
      "id": 6,
      "tasks": ["6.2", "6.3", "6.4", "6.5", "7.1"]
    },
    {
      "id": 7,
      "tasks": ["7.2", "8.1"]
    },
    {
      "id": 8,
      "tasks": ["8.2", "9.1"]
    },
    {
      "id": 9,
      "tasks": ["9.2", "10.1", "10.2", "10.3", "10.4", "11.1", "7.3", "9.3"]
    },
    {
      "id": 10,
      "tasks": ["11.2", "13.1", "7.4", "9.4"]
    },
    {
      "id": 11,
      "tasks": ["13.2", "14.1", "15.1"]
    },
    {
      "id": 12,
      "tasks": ["14.2", "16.1"]
    },
    {
      "id": 13,
      "tasks": ["17.1"]
    },
    {
      "id": 14,
      "tasks": ["18.1", "19.1", "20.1"]
    },
    {
      "id": 15,
      "tasks": ["18.2", "19.2", "20.2", "21.1"]
    },
    {
      "id": 16,
      "tasks": ["21.2", "21.3", "22.1", "23.1", "24.1"]
    },
    {
      "id": 17,
      "tasks": ["25.1"]
    },
    {
      "id": 18,
      "tasks": ["25.2", "26.1"]
    },
    {
      "id": 19,
      "tasks": ["27.1"]
    },
    {
      "id": 20,
      "tasks": ["28.1", "28.2", "28.3", "28.4", "28.5", "28.6", "28.7", "28.8"]
    },
    {
      "id": 21,
      "tasks": ["28.9", "29.1"]
    },
    {
      "id": 22,
      "tasks": ["29.2", "30.1"]
    },
    {
      "id": 23,
      "tasks": ["30.2", "31.1"]
    },
    {
      "id": 24,
      "tasks": ["32.1", "31.2"]
    },
    {
      "id": 25,
      "tasks": ["33.1"]
    },
    {
      "id": 26,
      "tasks": ["34.1"]
    },
    {
      "id": 27,
      "tasks": ["34.2", "35.1"]
    },
    {
      "id": 28,
      "tasks": ["35.2", "36.1"]
    },
    {
      "id": 29,
      "tasks": ["37.1", "37.2"]
    },
    {
      "id": 30,
      "tasks": ["38.1"]
    },
    {
      "id": 31,
      "tasks": ["39.1", "39.3", "39.5", "39.7", "39.10", "39.14"]
    },
    {
      "id": 32,
      "tasks": ["39.2", "39.4", "39.6", "39.8", "39.9", "39.11", "39.12", "39.13"]
    },
    {
      "id": 33,
      "tasks": ["40.1", "40.2", "40.3", "40.5", "40.6"]
    },
    {
      "id": 34,
      "tasks": ["41.1"]
    },
    {
      "id": 35,
      "tasks": ["42.1"]
    },
    {
      "id": 36,
      "tasks": ["44"]
    },
    {
      "id": 37,
      "tasks": ["43", "43.1", "43.2", "44.1"]
    },
    {
      "id": 38,
      "tasks": ["47"]
    },
    {
      "id": 39,
      "tasks": ["45", "46"]
    },
    {
      "id": 40,
      "tasks": ["48", "49", "49.1"]
    },
    {
      "id": 41,
      "tasks": ["50", "50.1", "51"]
    },
    {
      "id": 42,
      "tasks": ["52", "52.1", "52.2", "52.3"]
    },
    {
      "id": 43,
      "tasks": ["39.15", "39.16", "39.17", "39.18", "39.19"]
    },
    {
      "id": 44,
      "tasks": ["53"]
    },
    {
      "id": 45,
      "tasks": ["54", "39.20", "39.21", "39.22"]
    },
    {
      "id": 46,
      "tasks": ["55"]
    },
    {
      "id": 47,
      "tasks": ["56"]
    },
    {
      "id": 48,
      "tasks": ["57"]
    }
  ]
}
```

---

## Merge Reconciliation Addendum (canonical merge of Kiro's updated tasks + prior reconciliation)

This file = Kiro's updated tasks.md (checkpoints 17/26/33/37/38/42 rewritten as concrete integration tests — adopted) + the reconciliation fixes below (which Kiro's branch did not contain). Phase numbering: **Phase 4 = PBT** (above); **Phase 5 = optional Temporal/Inngest**; **Phase 6 = optional predictive routing**.

### Corrections applied to existing tasks
- **Task 5 (Stop hook):** cap/no-progress now **allow** termination (exit 0) with `status=handoff` + summary; only the unproven-items case blocks (exit 2). *(REQ-LOOP-005 — fixes a force-continuation/infinite-block defect that persisted in Kiro's branch. Properties 8 and 9 should additionally assert exit 0 on the HANDOFF path, not only that status==handoff.)*
- **Harness references:** all `formal_verification.py` references point to the canonical **`formal_verification_merged.py`** (**34/34** checks: 14 core + 12 Kiro + 8 new); the harness self-counts its assertion groups (CHECK-1..5c core, CHECK-6a..9c Kiro, CHECK-10a..13b new). The deprecated `formal_verification.py` and its "21 checks" wording are superseded and must not be cited.
- **Dependency-graph count:** the graph has 36 waves (ids 0–35) for tasks 1–42, plus appended waves (ids 36–48) that schedule the new tasks 43–57 (tasks 54/55/56 are waves 45/46/47; the flagd build task 57 is wave id 48). *(Reconciliation 2026-06-16: the prior note under-reported by 5 waves and stopped at task 53 — task 57 IS scheduled (wave 48); corrected to match the actual waves JSON, which runs through wave id 48. Reconciliation 2026-06-15: no "35 waves total" statement exists in this file; the prior off-by-one note was itself spurious and has been removed.)*

### Added tasks — close untasked requirements (found in audit)
- [ ] 43. Orchestration wiring (**Requirement 15**, previously untasked) — wire subagent/hook inner loop (initializer/implementer/verifier/research); no external agent-reasoning framework by default. _Requirements: 15.1_
  - [ ] 43.1 Phase 5 (optional) Temporal/Inngest durable stub behind a flag — `claude -p` as a durable step, each tool call a separate activity. _Requirements: 15.2_
  - [ ] 43.2 Assert Agent_Teams stays off the gating path. _Requirements: 15.3_
- [ ] 44. Execution-bounds config module (**Requirement 20**, previously untasked) — centralize numeric DEFAULTs (coverage 85%, slice ≤15m, cap 25, retries 3, loop 7, timeout 60s, export ≤5s) with explicit operator-override checks. _Requirements: 20.1, 20.2_
  - [ ] 44.1 **Role registry — single-source the privileged-actor literal (COH-1 / HGD-3).** The module MUST ALSO expose the privileged-actor role name as a single constant `VERIFIER_ROLE` (DEFAULT `"verifier.md"`, operator-overridable via env `SDLC_VERIFIER_AGENT`). EVERY actor gate and fixture — `subagent_stop_hook.py`, `pre_tool_use_hook.py`, `tools/store.py`, `tools/coverage.py`, and the spine tests `tests/spine/test_subagent_stop_actor.py` / `test_pre_tool_use_authority.py` — MUST IMPORT `VERIFIER_ROLE` from this module instead of re-declaring the byte-literal `"verifier.md"` locally (today it is hardcoded in 5+ files: subagent_stop_hook.py:30, pre_tool_use_hook.py:25, store.py:95, coverage.py:21, prove_trivial_slice.py:55). A rename then becomes a one-line change, not a brittle multi-file byte-edit. The constant's DEFAULT MUST agree byte-for-byte with the agent frontmatter `name:` (`verifier.md`, edit AI-01).
    - Add a CI assert (`tests/unit/test_verifier_role_single_source.py`): grep the hooks/tools for a local `VERIFIER_AGENT = "..."`/`VERIFIER_ROLE = "..."` assignment and FAIL if any module re-declares the literal instead of importing it; AND assert that, given `CLAUDE_AGENT_NAME = VERIFIER_ROLE`, `tools.actor_identity.resolve_identity(...).actor_agent == VERIFIER_ROLE` (proves the resolved runtime identity equals the single-source constant the gates compare).
    - _Requirements: 20.1, 20.2, 9.2 (role-separation literal)_
- [ ] 45. Secrets-detection gate (**criterion 17.2**, previously untasked) — CI step (gitleaks/trufflehog) blocking commit/merge on a detected secret in a diff. Registered as the REQUIRED `secrets-scan` status check via `.github/workflows/secrets-scan.yml` (see task 40.2) and in `docs/github-ruleset.md`. *(Reconciliation 2026-06-15: this is a REQUIRED merge gate, not advisory.)* _Requirements: 17.2_
- [ ] 46. Sandbox isolation (**criterion 17.4**, previously untasked) — run agent-executed/untrusted code inside an isolated sandbox. *(Reconciliation 2026-06-15: default = devcontainer locally / E2B for ephemeral CI; network egress DENIED by default; filesystem writes confined to the per-slice git worktree mounted into the sandbox — the worktree is the unit of isolation mounted in, the sandbox is the security boundary.)* _Requirements: 17.4_
- [ ] 47. WIRING integration-test evidence (**criterion 8.3**, previously untasked) — a WIRING item flips `proven` only with an integration test exercising the real execution path attached as Evidence_Record. _Requirements: 8.3_

### Added tasks — new gap-closure requirements (from the 95-pain-point coverage audit)
- [ ] 48. Requirement-amendment versioning (**REQ-COV-007**) — `requirement_versions` table (migration `db/migrations/007_requirement_versions.sql`, task 28.7); on amendment re-enter `unproven`; block COMPLETE while any amended item un-reproven. Only `*→proven` requires a complete Evidence_Record. Property 25 (test in task 39.15). _Z3 CHECK-10a/10b._ _Requirements: 22 (REQ-COV-007)_ *(Reconciliation 2026-06-16: parent task 48 was previously uncited; standardized to Requirement 22.)*
  - [ ] 48.1 Amendment producer/caller `tools/amendment_handler.py` *(Reconciliation 2026-06-16: the table could be created but nothing populated it or triggered the status reset; mirrors the audit_log producer pattern.)* — expose `record_amendment(requirement_id, new_text, author, rationale)` that, in a single transaction, (1) inserts the next `requirement_versions` row and (2) resets the linked `coverage_items.status` to `unproven`. Invoking actor = a human operator action, NOT an autonomous agent. _Requirements: 22 (REQ-COV-007)_
- [ ] 49. Resumed-state integrity (**REQ-STATE-005**) — new `tools/state_integrity.py` recomputes the resumed-state hash vs the durable store. *(Reconciliation 2026-06-15: the `SessionStart` hook stays NON-BLOCKING but COMPUTES the resumed-state hash and writes `run_state.resume_integrity_ok` (bool); a NEW PreToolUse "integrity guard" check (task 49.1) BLOCKS the first write (exit 2) when `resume_integrity_ok` is false, because SessionStart cannot block.)* Property 26 (test in task 39.16). _Z3 CHECK-11a/11b._
  - [ ] 49.1 PreToolUse integrity-guard check (**REQ-STATE-005 enforcement point**) — add a check to `.claude/hooks/pre_tool_use_hook.py` that reads `run_state.resume_integrity_ok` and BLOCKS the session's first `Write`/`Edit`/`MultiEdit` with exit 2 when it is false; chain it before the existing plan/scope/artifact/status checks. *(Reconciliation 2026-06-15: the gate moves from SessionStart to PreToolUse.)* _Requirements: REQ-STATE-005_
  - [ ] 49.2 SessionStart compute/write of `resume_integrity_ok` (**Phase-2 extension of the Phase-0 hook**) *(Reconciliation 2026-06-16: this write was previously untasked — design and Property 26 state SessionStart computes the resumed-state hash and writes `run_state.resume_integrity_ok`, but task 7.1 only did git/progress/coverage load + stdout injection and task 49/49.1 created `state_integrity.py` + the PreToolUse guard with no subtask wiring `state_integrity` INTO `session_start_hook.py`.)* — extend `.claude/hooks/session_start_hook.py` to import `tools/state_integrity.py`, call `state_integrity.compute_hash()`, compare against the durable `run_state.state_hash`, and write `run_state.resume_integrity_ok`; remains NON-BLOCKING (exit 0 always). Cross-referenced from task 7.1; the assertion that `resume_integrity_ok` is written on resume is added to task 7.2's unit tests. _Requirements: 11.3, REQ-STATE-005_
- [ ] 50. Checklist-approval gate + research epistemic integrity (**REQ-SPEC-016/017**) — DRAFT checklist cannot be used (Z3 CHECK-12); require source URL + authority-tier label + independent fact-check on all Research_Sub_Agent claims before human review. Properties 27, 29. _Requirements: 24.1 (REQ-SPEC-016), 24.2 (REQ-SPEC-017); 3.1, 3.3 (sourcing context)._ *(Reconciliation 2026-06-16: was "3.1, 3.3" only — those are Requirement 3's sourcing criteria, not the requirements task 50 closes; task 50 implements REQ-SPEC-016 (Req 24.1) AND REQ-SPEC-017 (Req 24.2).)*
  - [ ] 50.1 Add `check_checklist_approval(event)` to `.claude/hooks/pre_tool_use_hook.py` *(Reconciliation 2026-06-16: the design hook-wiring checklist-approval row, Property 27, and CHECK-12 existed but no build task previously named this concrete hook check; task 50 implemented only the abstract gate logic. Mirrors the task 49.1 integrity-guard subtask.)* — block any Initializer/discovery `Write` that references a domain-baseline checklist whose `approved_at` is NULL in `domain_baseline_checklists`; chain it with the existing plan/scope/artifact/status PreToolUse checks (and the 49.1 integrity guard) in the order pinned at task 6.1. NOTE: task 6.1's four named checks (`check_plan_approval`, `check_scope_sequencing`, `check_artifact_guard`, `check_status_transition`) are NOT the complete PreToolUse hook — the checklist-approval check is added here (50.1) and the integrity guard by 49.1, so the hook is not "complete" at task 6. _Requirements: 24.1 (REQ-SPEC-016)._
- [ ] 51. Performance / accessibility / UI-completeness verification (**REQ-VERIFY-007/008**) — amend `.claude/agents/verifier.md` (authored in task 10.3) to add the fifth perf / a11y / UI-render verification layer (the `perf_a11y_verifier` capability): k6/Lighthouse perf budgets (p95, Core Web Vitals) + axe-core (0 WCAG-A/AA violations) as NFR Evidence_Records; assert every declared screen/state (incl. empty/loading/error) has a render test. Validates Property 31 (perf/a11y evidence) via `tests/property/test_perf_a11y.py`. *(Reconciliation 2026-06-16: (1) reworded from "implement a `perf_a11y_verifier` component in the Verifier" to "amend `.claude/agents/verifier.md`" so the capability has a concrete host file (authored in task 10.3); (2) DELETED the mis-cited "Validates Property 23 line-coverage figures via pytest-cov … coverage.json" sentence — Property 23 validates Req 9.6 line-coverage, a wholly distinct concern from REQ-VERIFY-007/008; that conflation gave perf/a11y a borrowed, wrong test reference. Property 23 remains owned by task 39.12 / 10.3.)* _Requirements: REQ-VERIFY-007/008 (was "9.x" — corrected 2026-06-15)._
  - [ ] 51.1 Add a perf/a11y CI execution step so the `perf_a11y_verifier` capability has an execution path in CI *(Reconciliation 2026-06-16: task 1 (line 15) pins `k6` / Lighthouse / `@axe-core/playwright` but no workflow ran the perf/a11y/render checks, so the capability had no CI execution path — this mirrors the Playwright step in task 15.1.)*
    - Extend `.github/workflows/coverage-gate.yml` (or add a dedicated `perf-a11y` job) that, for NFR-subtype coverage items, installs and runs the k6 perf-budget check, the Lighthouse/Core-Web-Vitals check, and the axe-core (`@axe-core/playwright`) WCAG-A/AA scan, and the per-screen render checks; upload the k6 / Lighthouse / axe-core result artifacts (the NFR Evidence_Record `output_bytes` source per task 3.1) on failure
    - _Requirements: REQ-VERIFY-007/008_
- [ ] 52. Tamper-evident gate-decision audit log + reasoning-loop detection (**REQ-AUDIT-001..003, REQ-OBS-006**) — append-only hash-chained `gate_audit_log` table (migration `db/migrations/008_gate_audit_log.sql`, task 28.8; each entry stores prior-entry hash); a chain-verifier fails on any broken link; flag repeated-action loops (≥ K=3 identical tool-call signatures). *(Reconciliation 2026-06-15: implement the REASONING span as a custom span ATTRIBUTE `claude.span.kind="reasoning"` on an OTel INTERNAL span — NOT a new SpanKind enum value, since OTel SpanKind is a closed enum {INTERNAL,SERVER,CLIENT,PRODUCER,CONSUMER}.)* Property 28 (test in task 39.18). _Requirements: REQ-AUDIT-001..003, REQ-OBS-006 (was "12.x" — corrected 2026-06-15)._
  - [ ] 52.1 Audit-log PRODUCER `tools/audit_log.py` — expose `append(event, tool, decision, reason, requirement_id, actor_agent)`. *(Reconciliation 2026-06-15: it is CALLED by `stop_hook.py`, `pre_tool_use_hook.py`, and `subagent_stop_hook.py` on EVERY allow/block decision.)* Genesis entry uses `prev_hash = sha256("")`; canonical form = deterministic JSON of `(seq, event_name, tool_name, decision, reason, requirement_id, actor_agent, created_at)`; `entry_hash = sha256(canonical_row || prev_hash)` and INCLUDES `seq` and `created_at`. *(Reconciliation 2026-06-16, chain-linearization / concurrency control:)* because the chain is strictly sequential and `entry_hash` includes the BIGSERIAL `seq`, two concurrent `append()` calls from different hook processes that read the same `prev_hash` but receive distinct `seq` values would FORK the chain at identical `prev_hash` — exactly the condition `audit_verify` treats as tampering (Property 28), a guaranteed false positive that would brick the merge gate. `append()` MUST serialize the prev_hash-read + insert under a lock (e.g. `pg_advisory_xact_lock` keyed on the log, or `SELECT … FOR UPDATE` on a chain-head sentinel) within ONE transaction so the chain linearizes. (Mirror this as an Error-Handling note in design.) _Requirements: REQ-AUDIT-001._
  - [ ]* 52.4 Write unit tests for `tools/audit_log.py` (write-side) *(Reconciliation 2026-06-16: the security-critical producer had no unit-test subtask of its own — only the indirect Property 28 PBT (task 39.18), which exercises `audit_verify.py`.)*
    - Assert (a) genesis `prev_hash == sha256("")`; (b) `entry_hash` determinism for a fixed input tuple (`(seq, event_name, tool_name, decision, reason, requirement_id, actor_agent, created_at)`); (c) a round-trip `append` → `audit_verify` passes on an intact chain
    - _Requirements: REQ-AUDIT-001._
  - [ ] 52.2 Audit-chain verifier `tools/audit_verify.py` — recompute the chain and fail on any broken link. *(Reconciliation 2026-06-15: verification trigger = the REQUIRED `audit-chain-verify` CI status check at merge (task 40.3) PLUS on-demand invocation.)*
    - *(Reconciliation 2026-06-16, merged-chain (DB + file-backed) verification:)* when Postgres is unavailable the verifier reads BOTH the `gate_audit_log` table AND any file-backed log segments the producer wrote under DB-down (Note N-25), orders the merged entries by `seq`, and verifies the single combined chain. Seam rule: the file segment's first `prev_hash` MUST chain to the DB segment's last `entry_hash` (and vice-versa on reconnect). Without this the verifier has no rule for a chain split across Postgres + a file-backed log, so a split chain could falsely fail at the seam or be silently skipped.
    - *(Reconciliation 2026-06-16, structured failure report:)* on a broken link, emit a machine-readable JSON report to stdout — `first_broken_seq`, `expected_hash`, `stored_prev_hash`, `computed_prev_hash` — IN ADDITION to the non-zero exit, so the `audit-chain-verify` CI check (task 40.3) can annotate the specific failing entry rather than only an opaque non-zero exit.
    - *(Reconciliation 2026-06-16, REQ-AUDIT-003 joint satisfaction:)* REQ-AUDIT-003 (retain the log as an execution-proof complement to SLSA) is satisfied JOINTLY by migration 008 (retention / append-only storage) + this verifier (proof) + the SLSA release workflow (task 32.1).
    - _Requirements: REQ-AUDIT-002, REQ-AUDIT-003._ *(Reconciliation 2026-06-16: added REQ-AUDIT-003 to match the design attribution of BOTH REQ-AUDIT-002 and REQ-AUDIT-003 to `audit_verify.py`; the verifier's retention/proof obligation was previously mapped only on producer-wiring subtask 52.3.)*
  - [ ] 52.3 Wire audit-log producer into the three hooks — modify `stop_hook.py`, `pre_tool_use_hook.py`, and `subagent_stop_hook.py` to call `tools/audit_log.append(...)` on every allow/block decision (the producer-wiring task). *(Reconciliation 2026-06-16: ordering/robustness — for `subagent_stop_hook.py` (and the other two hooks) the `audit_log.append(...)` call MUST be invoked INSIDE the decision path BEFORE the exit, wrapped so an append failure degrades to the file-backed log (Note N-25 fallback) and NEVER suppresses or skips the gate decision/exit. Otherwise the fail-closed unhandled-exception exit 2 (task 8.1) could fire before any audit entry is written, breaking REQ-AUDIT-001's "on every allow/block decision" obligation. Add a unit test: `audit_log.append` raises (e.g. Postgres down before the file-fallback engages) → the allow/block decision is still recorded to the file-backed log AND the hook exits with the correct code.)* *(Reconciliation 2026-06-16, audit-completeness scope start point:)* the producer is wired into its caller hooks ONLY at this subtask, so REQ-AUDIT-001's "append every gate decision" invariant (requirements.md:457) begins at task 52.3 — gate decisions made by the Stop / PreToolUse / SubagentStop hooks BEFORE 52.3 lands (Phase 0/1 and most of 2/3) are intentionally OUT of audit scope. The append wiring needs only the file-backed fallback (no Phase-2 DB dependency), so an implementation MAY pull this wiring earlier to make the chain complete from Phase 0; absent that, pre-52.3 decisions are unlogged by design. _Requirements: REQ-AUDIT-001, REQ-AUDIT-003._
- [ ] 53. (Optional, Phase 6) Predictive routing — read-only, off the gate (REQ-PRED-*); only after the spine is proven.

### Added tasks — P3 market-research capabilities (Tier-1 industry-standard enrichment)
- [ ] 54. Structured Omission Declaration gate (**REQ-SPEC-018**, Property 30) — **Phase 0 capability** *(Reconciliation 2026-06-16: the omission_guard is a Phase-0 component and its host `subagent_stop_hook.py` hosts only Phase-0 gates; pin its phase explicitly as Phase 0. The guard is delivered by this task and MUST be runnable end-to-end (alongside task 8's `subagent_stop_hook.py`) before Phase 1, even though the task text sits in this appended block.)* — add `omission_declaration` as a required non-nullable field to each subagent output schema (initializer, research, verifier); extend `subagent_stop_hook.py` with an omission-declaration guard that rejects (exit 2) any result whose `omission_declaration` is null or absent; update `omission_guard` component. Property 30 test in subtask 39.20. *(P3 market-research 2026-06-15: Spec-Kit `[Gap]` pattern. Z3 CHECK-13a/13b.)* _Requirements: REQ-SPEC-018_
- [ ] 55. Eval-gating in CI (**REQ-EVAL-001**) — implement `tools/deepeval_gate.py` with DeepEval `assert_test()` for configured metric thresholds (faithfulness ≥ 0.8, answer relevancy ≥ 0.7); register `deepeval-gate` as a REQUIRED CI status check at merge. *(P3 market-research 2026-06-15: DeepEval pytest-native, fits existing pytest/Hypothesis stack.)* _Requirements: REQ-EVAL-001_
  - [ ] 55.1 Create `.github/workflows/deepeval-gate.yml` and register `deepeval-gate` as a REQUIRED status check *(Reconciliation 2026-06-16: task 55 implemented only the Python module; unlike zap-baseline (task 56) and secrets-scan/audit-chain-verify (40.2/40.3), no task created the workflow file or registered the ruleset gate, so the "REQUIRED CI status check at merge" claim had no workflow/registration behind it. The required-check registration is also folded into the Phase-4 task-40.5 subtask below.)* — run `pytest tools/deepeval_gate.py` (or `deepeval test run`); trigger on `pull_request`; add the workflow to the GitHub repository ruleset as a required check (canonical list = task 14.2); document in `docs/github-ruleset.md`. _Requirements: REQ-EVAL-001 (REQ-EVAL-001.3)_
- [ ] 56. DAST baseline security scan (**REQ-SEC-008**) — add `.github/workflows/zap-baseline.yml` using `zaproxy/action-baseline@v0.12.0` with `fail_action: true`, triggered `on: pull_request` (optionally with a target-branch filter for the protected branch) so REQ-SEC-008.1's "on every PR" prose has a concrete mechanism *(Reconciliation 2026-06-16: no canonical file previously defined any `on:` block / branch filter / event scope for zap-baseline; mirrors task 41.1's "Trigger on every `pull_request`".)*; register `zap-baseline` as a REQUIRED CI status check (canonical required-checks list = task 14.2; registration folded into Phase-4 subtask 40.4); baseline passive scan only — active/full scan out of v1 scope. *(P3 market-research 2026-06-15: OWASP ZAP, zero-config baseline.)* _Requirements: REQ-SEC-008_
- [ ] 57. Agent kill-switch (**REQ-CTRL-001**) — deploy self-hosted flagd service (`flagd/` directory, Apache 2.0, CNCF Incubating); wire OpenFeature SDK into agent entry points; verify near-real-time flag propagation (≤ 30 s) without process restart. *(P3 market-research 2026-06-15: OpenFeature + flagd, self-hosted, no SaaS dependency.)*
  - *(Reconciliation 2026-06-16, concrete provider + ≤30s backing:)* pick ONE propagation mechanism rather than leaving "file-based or gRPC" open: EITHER **gRPC streaming** (near-instant propagation) OR **file-based polling with an explicit poll interval ≤ 30 s**; tie the ≤30 s verification step to the chosen provider's mechanism so the guarantee is testable.
  - *(Reconciliation 2026-06-16, scaffold deliverables:)* create the `flagd/` directory with a flag-definitions file (`flagd.json`), provider config, and a self-hosted deployment manifest; define the kill-switch flag schema enumerating the flag name(s) and the gated agent capabilities (initializer / implementer / verifier / research per task 10.2's kill-switch instrumentability note).
  - *(Reconciliation 2026-06-16, instrumented entry points — REQ-CTRL-001.2:)* "wire OpenFeature SDK into agent entry points" names the four agents as kill-switchable capabilities whose capability is checked against the flagd flag before a slice starts, so the affected agent capability can be disabled within ≤ 30 s without process restart.
  - _Requirements: REQ-CTRL-001_

### Added correctness properties (extend the PBT suite to 30)
- Property 25: Amendment monotonicity (CHECK-10). Property 26: Resumed-state integrity (CHECK-11). Property 27: Checklist-approval-before-use (CHECK-12). Property 28: Audit-log tamper detection (REQ-AUDIT-002). Property 29: Research-claim authority labeling + fact-check (REQ-SPEC-017). Property 30: Omission-declaration gate (REQ-SPEC-018, CHECK-13a/13b).
