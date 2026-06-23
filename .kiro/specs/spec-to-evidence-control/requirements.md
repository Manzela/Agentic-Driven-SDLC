# Requirements Document

## Introduction

The Spec-to-Evidence Coverage Control System is an autonomous agentic software-delivery control plane that runs on the Claude Code substrate. Its purpose is to minimize human micro-steering by converting product intent into a traceable, machine-verifiable coverage model that governs agent execution and rejects incomplete delivery.

The governing invariant: **deterministic gates — Claude Code hooks, CI, OPA — decide whether delivery is complete, computed solely from verifiable facts. Model self-assessment and probabilistic predictions only inform; they never gate.**

The system is structured around 19 domain-baseline capability blocks (B01–B19) and is specified by **32 numbered requirements** (Requirement 1–32 — 20 original plus 12 added: Req 21–28 in the Merge Reconciliation Addendum, Req 29–32 in the P3 Market-Research Addendum), verified by a unified Z3 formal-verification harness (`verification/formal_verification_merged.py`, which on `python3 verification/formal_verification_merged.py` self-asserts **34/34 machine-checked assertions** — re-run it to confirm; the count is the harness's own SAT/UNSAT self-count, not a frozen claim — groups: 14 core (CHECK-1..5c) + 12 Kiro (CHECK-6a..9c) + 8 new (CHECK-10a..13b)). The minimum viable spine (Phase 0) consists of: `feature_list.json` + Stop hook + independent verifier subagent + git worktrees + GitHub required status check + Playwright behavioral proof. *(Reconciliation 2026-06-15: the deprecated `formal_verification.py` and its "21 checks" figure are never cited; the merged harness self-counts to 34.)*

The delivery plan comprises **five required phases (0–4) plus two optional phases (5–6)**. Out of scope for v1: Agent Teams peer-to-peer (experimental); Temporal/Inngest durable outer loop (optional Phase 5); predictive next-step routing (optional Phase 6, off-gate); full EU AI Act legal conformity packaging; and deductive correctness proof of generated code. NOTE: performance AND accessibility verification are now IN scope via REQ-VERIFY-007/008 (this corrects the prior out-of-scope exclusion).

---

## Glossary

- **System**: The Spec-to-Evidence Coverage Control System as a whole.
- **Spec_Compiler**: The component responsible for transforming product intent into atomic, individually-testable requirements with IDs and acceptance criteria (realized by `.claude/agents/initializer.md` — Phase 0; see design.md Subagent Definitions).
- **Coverage_Model**: The machine-readable map of every required feature/behavior/NFR, embodied in `feature_list.json`, that defaults every item to `unproven`.
- **Verifier**: The independent evaluator subagent that performs completion verification. It has no write access to the implementation and does not verify its own output.
- **Completion_Gate**: The deterministic enforcement layer (Stop hook + OPA/Conftest CI check + GitHub required status check) that blocks delivery from being declared complete while any in-scope requirement is `unproven`.
- **PreToolUse_Hook**: The Claude Code `PreToolUse` hook — the sole true prevention gate (exit 2 blocks before execution). Not to be confused with `PostToolUse`, which cannot undo an already-executed action.
- **Stop_Hook**: The Claude Code `Stop` hook that blocks agent termination when the coverage model contains any `unproven` in-scope item.
- **SubagentStop_Hook**: The Claude Code `SubagentStop` hook that validates evidence schema AND enforces the omission-declaration gate (rejects any subagent result whose `omission_declaration` is absent/null, exit 2) before accepting a subagent's result.
- **omission_declaration**: A structured field on initializer/research/verifier subagent outputs, keyed by the six EARS scenario categories (Primary / Alternate / Exception / Recovery / Non-Functional / Edge-Case), each a list of `[Gap]`-marked uncovered scenario classes; required and non-null (Requirement 29 / REQ-SPEC-018). The SubagentStop omission-declaration guard checks presence/non-null only; the per-category content is a human-reviewed authoring convention.
- **PostToolUse_Hook**: The Claude Code `PostToolUse` hook — a next-turn forcing function only; it cannot undo an already-executed action.
- **PreCompact_Hook**: The Claude Code `PreCompact` hook that checkpoints progress before context compaction.
- **SessionStart_Hook**: The Claude Code `SessionStart` hook that restores run state at the start of a session, and computes the resumed-state integrity hash, writing `run_state.resume_integrity_ok` (non-blocking; enforced by the PreToolUse integrity guard, Requirement 23).
- **Resumed-State Hash**: The SHA-256 computed at session resume over the canonical serialization of the durable + file run state (the same hash-algorithm/canonical-form spec used by the design hash layer). Compared against the Recorded State Hash to detect false or corrupted resumption (Requirement 23).
- **Recorded State Hash**: The baseline state hash persisted in `run_state.state_hash` at the last clean checkpoint; the durable store's recorded value against which the Resumed-State Hash is compared.
- **Operator Reconciliation**: The human-driven re-record-and-unblock action that, after a Resumed-State Hash vs Recorded State Hash mismatch, re-establishes the recorded baseline and flips `run_state.resume_integrity_ok` to `true`, releasing the PreToolUse integrity guard (Requirement 23).
- **feature_list.json**: The canonical, version-controlled coverage-model file. Every in-scope item appears here with type, status, dependencies, acceptance criteria, `in_scope`, and (when proven) an Evidence_Record.
- **Progress_File**: The version-controlled `claude-progress.txt` checkpoint that SessionStart reads and PreCompact writes.
- **Evidence_Record**: A structured record with exactly four required fields: `test_file`, `test_name`, `output_hash`, `collected_at`. An item cannot transition to `proven` without all four fields present.
- **Slice**: A bounded unit of implementation work, targeting ≤15 minutes / ≤1 feature, implemented in a dedicated git worktree and resulting in one atomic commit.
- **EARS**: Easy Approach to Requirements Syntax — the requirements-expression standard used throughout. Patterns: five base patterns — Ubiquitous, Event-driven, State-driven, Unwanted behaviour, Optional — plus Complex, which is a *documented composition* of the five base patterns, NOT a sixth assignable enum value. The `feature_list.json` `ears_pattern` enum (design.md:347), `spec_validator.py`, Req 1.4, and Property 16 operate only over the five base patterns. *(Reconciliation 2026-06-16: the six-vs-five mismatch is resolved per design.md:1187–1188 — Complex composes the five; no schema change.)*
- **UNMAPPED**: A flag assigned to any domain-baseline item that has zero proposed requirements after discovery; an UNMAPPED item blocks advancement to implementation.
- **HANDOFF**: A terminal state distinct from COMPLETE, assigned when iteration cap, cost budget, or the no-progress predicate is reached. A HANDOFF run is never marked COMPLETE.
- **COMPLETE**: A terminal state assigned only when every in-scope requirement is `proven` with attached evidence and all gates pass.
- **WIRING**: A coverage-item type representing architectural connection obligations (routes, handlers, callbacks, jobs that must be reachable from a real execution path).
- **OPA_Conftest**: The Open Policy Agent / Conftest policy engine used as a required CI status check to enforce zero-evidence blocking at merge.
- **SLSA**: Supply-chain Levels for Software Artifacts — the provenance framework used to sign build artifacts.
- **OTel**: OpenTelemetry — the observability framework used to emit spans for every model call, tool invocation, and subagent task.
- **W3C_Baggage**: The W3C Baggage propagation mechanism used to carry `requirement.id` across all child telemetry spans.
- **Langfuse**: The default managed observability backend (MIT core license).
- **Research_Sub_Agent**: A subagent that queries competitive analysis, industry standards, and open-source reference implementations to draft domain-baseline checklists for a new product class.
- **Domain_Baseline_Checklist**: A version-controlled artifact naming the essential capability blocks for a detected product class, used to drive proactive discovery.
- **plan-approved.json**: The approval marker file whose presence is required before any implementation Write/Edit tool is permitted. It carries a `feature_list_sha` binding its approval to a specific `feature_list.json` (the PreToolUse_Hook blocks implementation when the marker's `feature_list_sha` ≠ the canonical SHA-256 of the current coverage model — see Requirement 18.4) and a free-text `notes` field carrying the human's missing-context injection (consumed by the Initializer on the next session — see Requirement 18.2).
- **Postgres**: The managed relational database used as the durable store for requirements, coverage state, traceability links, evidence, run state, requirement-amendment history, and the gate-decision audit log. *(Reconciliation 2026-06-16: now an eight-table durable store — see design.md:427; amendment history and gate-decision audit log added as first-class tables via migrations 007/008.)*
- **Temporal_Inngest**: Optional durable-execution engines (Temporal or Inngest) for wrapping the inner loop in crash-safe multi-hour/multi-day runs. Off by default.
- **Agent_Teams**: The experimental Claude Code peer-to-peer multi-agent feature. Kept off the delivery-gating path until it exits experimental status.
- **Semgrep_CodeQL**: The SAST tools used in CI to detect HIGH/CRITICAL security findings in changed code.
- **DAST**: Dynamic Application Security Testing — black-box scanning of a running application; here the OWASP ZAP baseline passive scan (Requirement 31 / REQ-SEC-008).
- **Secrets_Scanner**: The CI tool (gitleaks by default; trufflehog as an acceptable alternative) used to detect committed secrets/credentials/tokens in a PR diff and fail the build (Requirement 17.2).
- **Playwright**: The E2E test framework used to produce behavioral proofs (captured traces/screenshots) as evidence.
- **Faithfulness**: A DeepEval RAG-style metric scoring how well an LLM `actual_output` is grounded in its supplied `retrieval_context` (no unsupported claims); gated at a DEFAULT threshold of 0.8 by the `eval-gate` (Requirement 30).
- **Answer relevancy**: A DeepEval RAG-style metric scoring how well an LLM `actual_output` addresses the given `input`; gated at a DEFAULT threshold of 0.7 by the `eval-gate` (Requirement 30).
- **Eval-gate (`deepeval-gate`)**: The DeepEval pytest-native eval step (`tools/deepeval_gate.py`) that calls `assert_test()` on the configured metric thresholds and runs as a REQUIRED CI status check at merge under the `deepeval-gate` check name (Requirement 30 / REQ-EVAL-001).

---

## Requirements

### Requirement 1: Spec Compilation

**User Story:** As a product owner, I want terse intent compiled into atomic, individually-testable requirements with unique IDs and acceptance criteria, so the agent and I share one machine-checkable definition of scope.

**Baseline block:** B01 | **PRD references:** REQ-SPEC-001..004

#### Acceptance Criteria

1. THE Spec_Compiler SHALL compile product intent into atomic requirements, each with a unique ID, an EARS-pattern statement, a priority field, and ≥1 machine-checkable acceptance criterion.
2. IF a candidate requirement contains a non-deterministic adjective from the canonical vague-adjective reject-set {`fast`, `secure`, `scalable`, `optimized`, `efficient`, `reliable`, `performant`} (the authoritative seven-member set; the validator MAY extend it) without a quantified numeric bound, THEN THE Spec_Compiler SHALL reject it and require a quantified criterion before acceptance. *(Reconciliation 2026-06-16: the authoritative seven-member set is stated here so the scanner's coverage is requirement-backed, not test-backed only; referenced by Property 17 (design.md:1012) and Task 4.4 (tasks.md). Also registered in the Requirement 20 threshold registry.)*
3. THE Spec_Compiler SHALL persist compiled requirements as version-controlled artifacts in the repository, not in model context alone.
4. WHEN a requirement is authored or modified, THE Spec_Compiler SHALL validate it against the EARS schema and assign exactly one of the five EARS patterns (Ubiquitous, Event-driven, State-driven, Unwanted behaviour, Optional). *(Reconciliation 2026-06-16: the glossary's sixth pattern, "Complex," is a documented composition of these five — not a separate assignable enum value; see the glossary EARS entry, the `ears_pattern` enum at design.md:347, Property 16, and the resolution at design.md:1187–1188.)*

---

### Requirement 2: Proactive Discovery

**User Story:** As a founder with limited context, I want the system to infer the implied, industry-standard features I did not enumerate, so a complete competitive product is specified without me hand-listing every micro-feature.

**Baseline block:** B02 | **PRD references:** REQ-SPEC-010..012

*(Reconciliation 2026-06-16: the PRD label range REQ-SPEC-010..012 maps to this requirement's criteria so the IDs are no longer implicit-only: REQ-SPEC-010 = criterion 2.1 (baseline-checklist expansion), REQ-SPEC-011 = criterion 2.2 (UNMAPPED-blocks-advancement), REQ-SPEC-012 = criterion 2.3 (human confirmation + inferred-vs-stated provenance).)*

#### Acceptance Criteria

1. THE System SHALL expand product intent against a curated Domain_Baseline_Checklist for the detected product class and propose implied requirements for each baseline item.
2. IF any Domain_Baseline_Checklist item has zero proposed requirements after discovery, THEN THE System SHALL flag that item `UNMAPPED` and SHALL NOT advance to implementation.
3. WHILE proactive discovery is active, THE System SHALL present every inferred requirement for human confirmation and SHALL mark inferred-vs-stated provenance on each requirement.

---

### Requirement 3: Domain-Baseline Checklist Sourcing

**User Story:** As a product owner, I want domain-baseline checklists to be researched, version-controlled, and auditably linked to coverage, so discovery quality is not dependent on ad-hoc model knowledge.

**Baseline block:** B19 | **PRD references:** REQ-SPEC-013..015

*(Reconciliation 2026-06-16: the PRD label range REQ-SPEC-013..015 maps to this requirement's criteria so the IDs are no longer implicit-only: REQ-SPEC-013 = criterion 3.1 (Research_Sub_Agent drafts a checklist + human review before use), REQ-SPEC-014 = criterion 3.2 (version-controlled per-product-class persistence), REQ-SPEC-015 = criterion 3.3 (record checklist version and link to `feature_list.json` for auditable derivation).)*

#### Acceptance Criteria

1. WHEN a new product class is encountered for the first time, THE System SHALL run a Research_Sub_Agent that queries competitive analysis, industry standards, and open-source reference implementations to draft a Domain_Baseline_Checklist for that product class, and SHALL present the draft for human review before use.
2. THE System SHALL persist Domain_Baseline_Checklists as version-controlled artifacts in the repository, named by product class, so checklists accumulate across projects and do not need to be re-derived from scratch.
3. WHEN a Domain_Baseline_Checklist is used, THE System SHALL record which checklist version was used and link it to `feature_list.json` so the derivation is auditable.

---

### Requirement 4: Spec-Completion Loop

**User Story:** As an operator, I want spec elaboration to run until the spec is provably free of contradictions, ambiguities, and gaps — bounded so it cannot loop forever or declare itself done to escape — so I get a complete spec without endless token burn.

**Baseline block:** B03 | **PRD references:** REQ-SPEC-020..024

*(Reconciliation 2026-06-16: the PRD label range REQ-SPEC-020..024 maps to this requirement's criteria as follows so the IDs cited in design.md are no longer dangling: REQ-SPEC-020 = criterion 4.1 (non-LLM validator verdict), REQ-SPEC-021 = criterion 4.2 (the `violation_count > 0` Stop-block, exit 2), REQ-SPEC-022 = criterion 4.3 (no-progress → human handoff), REQ-SPEC-023 = criterion 4.4 (hard pass-cap handoff), REQ-SPEC-024 = criterion 4.5 (emit validated spec at `violation_count == 0`). The cap/HANDOFF tiebreak in criterion 4.6 governs the REQ-SPEC-021 vs REQ-LOOP-005 precedence.)*

#### Acceptance Criteria

1. THE System SHALL judge spec completeness with a non-LLM validator returning `{contradictions, ambiguities, uncovered, violation_count}`; the authoring agent SHALL have no vote in the completeness verdict.
2. WHEN the spec agent attempts to end its turn AND `violation_count > 0`, THEN THE Stop_Hook SHALL block termination and return the enumerated violations to the agent.
3. IF a spec-completion pass does not strictly reduce `violation_count` versus the prior pass, THEN THE System SHALL halt and hand off to a human rather than retrying infinitely.
4. IF the spec-completion loop reaches its hard pass cap (DEFAULT = 7 passes), THEN THE System SHALL halt to human handoff and surface the remaining violations.
5. WHEN `violation_count == 0`, THE System SHALL emit the validated spec and `feature_list.json` and request human plan approval before any implementation begins.
6. **Exit-code tiebreak (lex specialis):** AT the hard pass cap (7) WITH `violation_count > 0`, the REQ-LOOP-005 HANDOFF (exit 0, ALLOW termination) SHALL take precedence over the criterion-4.2 Stop-block (exit 2); the exit-2 block applies ONLY on passes *before* the cap, while the exit-0 HANDOFF wins at the cap. *(Reconciliation 2026-06-15: resolves the REQ-SPEC-021 exit-2 vs REQ-LOOP-005 exit-0 collision in favor of HANDOFF at the cap.)*

---

### Requirement 5: Coverage Model

**User Story:** As a delivery lead, I want one machine-readable map of every required feature, behavior, and NFR that defaults to "unproven," so completeness is a queryable fact rather than a claim.

**Baseline block:** B04 | **PRD references:** REQ-COV-001..006

#### Acceptance Criteria

1. THE System SHALL maintain `feature_list.json` in which every item has an ID, a type ∈ {functional, NFR, WIRING}, a dependencies list, acceptance criteria, and a status field defaulting to `unproven`.
2. IF a tool action would delete, reorder, or modify an existing coverage item's identity, THEN THE PreToolUse_Hook SHALL block it; status transitions SHALL proceed only along the permitted edges `unproven → proven`, `unproven → failed`, and `failed → unproven` (any transition *into* `proven` additionally requires a complete Evidence_Record). *(Reconciliation 2026-06-15: status guard widened to admit the `failed` state; see Requirement 5.8 and Property 3.)*
3. WHEN an item is set to `proven`, THE System SHALL require an attached Evidence_Record containing exactly four required fields: `test_file` (path to the test), `test_name` (unique test identifier), `output_hash` (content-addressed hash of the test output), and `collected_at` (ISO-8601 timestamp); the transition SHALL be rejected if any of the four fields is absent.
4. THE System SHALL represent architectural WIRING obligations and NFR items as first-class coverage items in `feature_list.json`, not as code comments or informal afterthoughts.
5. WHILE any in-scope item is `unproven`, THE System SHALL treat the deliverable as incomplete.
6. THE System SHALL define Evidence_Record as a structured record containing exactly four required fields (`test_file`, `test_name`, `output_hash`, `collected_at`); a status transition to `proven` SHALL be rejected if any of the four fields is absent or empty. *(Z3 CHECK-7a/7c verified: PASSED with missing `output_hash` or zero fields is UNSAT.)*
7. THE System SHALL carry a boolean `in_scope` field (DEFAULT = `true`) on every coverage item (in the CoverageItem JSON schema AND the `coverage_items` Postgres table); all completion and Stop gates SHALL count ONLY `in_scope` items, and an item SHALL leave scope (`in_scope = false`) ONLY by a human-authored transition. *(Reconciliation 2026-06-15: in-scope is now data, not an implicit assumption; out-of-scope is human-authored only.)*
8. THE System SHALL allow the status transitions `unproven → failed` (Verifier on a dead check) and `failed → unproven` (on retry/amendment); ONLY a transition to `proven` requires a complete Evidence_Record. *(Reconciliation 2026-06-15: the `failed` status is now first-class; see the PreToolUse status guard and correctness Property 3.)*

---

### Requirement 6: Traceability

**User Story:** As an auditor, I want every requirement linked forward to verification and every code unit linked back to a requirement, so end-to-end coverage is provable.

**Baseline block:** B05 | **PRD references:** REQ-TRACE-001..004

#### Acceptance Criteria

1. THE System SHALL maintain bidirectional links requirement ↔ implementation ↔ test ↔ evidence ↔ commit ↔ owner in the durable Postgres store.
2. WHEN a commit is created, THE System SHALL require ≥1 referenced requirement ID in the commit trailer.
3. IF an implementation unit references no requirement, or a requirement maps to no verification, THEN THE System SHALL fail the orphan-detection check and block the run.
4. THE System SHALL stamp the active `requirement.id` onto every telemetry span via a W3C_Baggage span processor so traceability is reconstructable from the live trace.

---

### Requirement 7: Incremental Execution Control

**User Story:** As an engineer, I want the agent forced to implement one bounded slice at a time in isolation, so it cannot one-shot a sprawling, partial change.

**Baseline block:** B06 | **PRD references:** REQ-EXEC-001..005

#### Acceptance Criteria

1. THE System SHALL restrict each coding subagent session to exactly one highest-priority `unproven` item.
2. WHILE a Slice is in progress, THE System SHALL isolate it in a dedicated git worktree to prevent cross-slice collisions.
3. THE System SHALL target a per-slice size of ≤15 minutes / ≤1 feature and SHALL produce one atomic commit per completed Slice.
4. IF no `plan-approved.json` approval marker exists, THEN THE PreToolUse_Hook SHALL block all implementation Write and Edit tools.
5. IF any prior-slice coverage item is `unproven`, THEN THE PreToolUse_Hook SHALL block initiation of a new worktree or new slice assignment, preventing forward progress until the prior item is verified. *(Z3 CHECK-6a verified: newSliceStarting ∧ priorItemUnproven is UNSAT.)*

---

### Requirement 8: Wiring Verification

**User Story:** As a reviewer, I want components that compile but are never connected to be detected, so "looks done" cannot pass as "is wired."

**Baseline block:** B07 | **PRD references:** REQ-EXEC-010..012

#### Acceptance Criteria

1. THE System SHALL run static call-graph and dead-code analysis on changed files and SHALL represent each wiring obligation as a WIRING coverage item in `feature_list.json`.
2. IF a handler, route, job, or callback exists but is unreachable from any real execution path, THEN THE Verifier SHALL mark the corresponding WIRING item `failed`.
3. WHEN a WIRING item is claimed `proven`, THE System SHALL require an integration test exercising the real execution path as the attached Evidence_Record.

---

### Requirement 9: Verification Engine

**User Story:** As a quality owner, I want behavior, semantics, and security verified by an evaluator that did not write the code, so the system never grades its own homework.

**Baseline block:** B08 | **PRD references:** REQ-VERIFY-001..006

#### Acceptance Criteria

1. THE System SHALL verify each Slice across five layers: structural (lint, type checking, AST analysis), semantic (unit and integration tests), behavioral (E2E via Playwright), security (SAST via Semgrep_CodeQL), and performance + accessibility (k6/Lighthouse against numeric budgets and axe-core for zero WCAG-A/AA violations, per REQ-VERIFY-007/008). *(Reconciliation 2026-06-15: fifth layer added; kept consistent with Requirement 25.)*
2. THE System SHALL perform completion verification with the independent Verifier that has no write access to the implementation; the implementer SHALL NOT verify its own output.
3. WHEN a behavioral check runs, THE Verifier SHALL produce a captured artifact (trace, screenshot, or test output) attached as an Evidence_Record.
4. WHEN a file edit completes, THE PostToolUse_Hook SHALL run lint, type-check (mypy), SAST (Semgrep), and wiring checks and, on failure, SHALL return the specific errors to the agent for correction on its next turn. (THE PostToolUse_Hook SHALL NOT be relied upon to undo the edit; see the PreToolUse_Hook for prevention.) *(Reconciliation 2026-06-16: enumerated full check set to match design.md:216 and task 18.1 (ruff + mypy + semgrep + wiring_checker). The structural-layer AST analysis of REQ-VERIFY-001 / criterion 9.1 is performed INSIDE `wiring_checker.py` via the `ast` module (task 19.1), so the wiring check subsumes the AST element — "lint + type + SAST + wiring" is not an omission of the structural-layer AST.)*
5. IF a subagent's result lacks required evidence markers, THEN THE SubagentStop_Hook SHALL block acceptance of that result.
6. THE System SHALL set the target line-coverage threshold on touched files to a numeric DEFAULT of 85% (configurable), failing the Slice if coverage falls below the threshold. *(Reconciliation 2026-06-15: the per-touched-file line-coverage figure is generated by pytest-cov (coverage.py) and read from `coverage.json`.)*

---

### Requirement 10: Completion Gate

**User Story:** As a delivery owner, I want "done" to be impossible while any requirement is unproven, enforced where the model cannot talk past it.

**Baseline block:** B09 | **PRD references:** REQ-GATE-001..005

#### Acceptance Criteria

1. THE System SHALL compute the completion verdict solely from verifiable facts — zero `unproven` in-scope items, passing tests, and present Evidence_Records — evaluated against the actual repository state.
2. IF the agent attempts to terminate as COMPLETE WHILE any in-scope requirement is `unproven`, THEN THE Stop_Hook SHALL block termination. *(Z3 CHECK-1, CHECK-3 verified.)*
3. WHEN a merge is attempted, THE OPA_Conftest required CI status check SHALL run and SHALL fail the merge if any approved requirement has zero passing evidence (the zero-evidence policy query MUST return 0 rows).
4. WHILE a Stop_Hook block is active, THE System SHALL set `stop_hook_active` to prevent the hook from re-triggering itself and SHALL release the flag only when the blocking condition clears.
5. THE Completion_Gate SHALL be fail-closed and non-bypassable by configuration; ambiguous states SHALL resolve to "blocked," not "passed."

---

### Requirement 11: Session Continuity and Durable State

**User Story:** As an operator of long runs, I want state to survive context limits and crashes, so work resumes exactly where it stopped.

**Baseline block:** B10 | **PRD references:** REQ-STATE-001..004

#### Acceptance Criteria

1. THE System SHALL persist all mutable run state outside model context, in files, git history, and the durable Postgres store.
2. WHEN context compaction is imminent, THE PreCompact_Hook SHALL checkpoint progress and evidence records before context is trimmed.
3. WHEN a session starts, THE SessionStart_Hook SHALL load git status, the progress file, and the Coverage_Model so a resumed session re-orients deterministically; it SHALL additionally COMPUTE the resumed-state hash and write `run_state.resume_integrity_ok` (bool) — but, being non-blocking, it SHALL NOT itself halt the run. *(Reconciliation 2026-06-15: SessionStart computes the integrity result; the actual block moves to a PreToolUse integrity guard — see Requirement 23.)*
4. THE System SHALL record an incremental commit per completed Slice as the durable execution trail and rollback point.
5. WHEN a session starts, resumes, or follows a compaction, THE SessionStart_Hook SHALL assert that the governance spine is registered — comparing the live registered hook events against `SPINE_REQUIRED_EVENTS` (DEFAULT = the five A1-registered events: SessionStart, PreToolUse, PostToolUse, SubagentStop, Stop; PreCompact is intentionally EXCLUDED from the required set until a registered PreCompact hook lands, per COH-2) — and SHALL inject a green `Spine wired: N governance event(s) registered` line when wired-as-scoped, and a LOUD `GOVERNANCE SPINE UNWIRED/PARTIAL: <missing events>` warning when unregistered, partial, or malformed. THE hook SHALL additionally inject a re-orientation block (current branch, in-scope unproven/proven counts, and the last HANDOFF reason from `run_state`). THE hook SHALL fail OPEN with a diagnostic on its own error and SHALL NOT block (exit 0 always). *(Reconciliation: the silent-spine canary — A5 — makes a future un-wiring LOUD instead of silent, closing C-HOOK-01/C-INTENT-02.)*

---

### Requirement 12: Observability

**User Story:** As an operator, I want a live, requirement-tagged trace of what the agent is doing and every gate decision, so I can observe and audit mid-flight.

**Baseline block:** B11 | **PRD references:** REQ-OBS-001..005

#### Acceptance Criteria

1. THE System SHALL emit OTel spans for every model call, tool invocation, and subagent task. *(Note: OTel GenAI semantic conventions are experimental as of mid-2026 — keep `OTEL_SEMCONV_STABILITY_OPT_IN=gen_ai_latest_experimental` and treat them as unstable; pin the `opentelemetry-sdk` and the GenAI semconv package versions in `requirements.txt`.)*
2. WHILE a run is in progress, THE System SHALL stream each span to the observability backend as it closes (export interval DEFAULT ≤ 5 seconds), not batched at run-end.
3. WHEN a hook makes a gate decision, THE System SHALL emit that decision — event, tool, allow/block, reason, requirement ID — to the same trace endpoint as agent spans.
4. THE System SHALL propagate the active `requirement.id` to all child spans via a W3C_Baggage span processor.
5. WHERE a managed observability backend is used, THE System SHALL document its license (Langfuse MIT core; SigNoz MIT Expat core; Arize Phoenix Elastic License 2.0 — source-available, not OSI, no hosted-service offering) so backend choice is compliance-aware.

---

### Requirement 13: Mid-Flight Steering

**User Story:** As a platform owner, I want the only thing that can halt or redirect a running agent to be deterministic hooks, so enforcement does not depend on the model's intentions.

**Baseline block:** B12 | **PRD references:** REQ-STEER-001..006

#### Acceptance Criteria

1. THE System SHALL treat Claude Code hooks — not prompts and not CLAUDE.md — as the sole deterministic mid-flight intervention layer.
2. THE System SHALL use THE PreToolUse_Hook as the only true prevention gate (exit code 2 / deny blocks before execution); THE PostToolUse_Hook SHALL be treated as a next-turn forcing function that cannot undo an already-executed action.
3. IF a tool call targets a protected artifact (tests, coverage-model schema, CI config) or a destructive operation, THEN THE PreToolUse_Hook command-type hook SHALL block it. THIS protection SHALL be keyed on the artifact PATH being written, not on the tool name: a `Bash` command that writes a protected path (via shell redirection, `tee`, `sed -i`, `cp`/`mv`, or an interpreter `-c`/heredoc write) SHALL be blocked exactly as a `Write`/`Edit`/`MultiEdit` to that path would be. *(Reconciliation: closes the `tee`/`sed -i`/`echo >` bypass — HGD-2, #63787; a `Write|Edit|MultiEdit`-only matcher is not sufficient.)*
4. THE System SHALL use command-type hooks for hard policy enforcement (which fail closed) and SHALL NOT use HTTP or MCP hooks for hard policy (which fail open).
5. THE System SHALL honor the hook exit-code contract: exit 0 = proceed, exit 2 = blocking error fed to the model via stderr, any non-zero exit other than 2 = non-blocking (exit 1 does NOT block).
6. No gate decision SHALL read a probabilistic prediction; gate outcomes SHALL depend only on verifiable facts. *(Z3 CHECK-5 verified: a differing prediction cannot produce a differing gate decision.)*
7. THE System SHALL maintain a repo-root `CLAUDE.md` durable-invariant anchor as the single home (CH-11) for session-invariant DOCTRINE — distinct from the deterministic gates of criterion 1: actor-independence (`verifier.md`-only status→`proven` flips and Evidence_Record production), human-owned artifacts (only a human writes `plan-approved.json` or flips `in_scope`), the canonical-source pin (`feature_list.json` is the one coverage source), and the named charter doctrines CH-01 (steer to the next action, never a bare verdict / single canonical source) and CH-10 (vary/escalate on repeat → HANDOFF, i.e. escalate-don't-re-inject), plus the predictions-never-gate and locate-the-oracle-before-any-done-claim doctrines. The PreToolUse and SubagentStop steering reason strings SHALL reference these invariants BY SHORT NAME (e.g. 'see actor-independence in CLAUDE.md') rather than restating them per fire; all numeric thresholds SHALL live in the execution-bounds registry (Requirement 20), never in `CLAUDE.md` (CH-15). *(Reconciliation: criterion 1 keeps CLAUDE.md OUT of the deterministic gate path; this criterion 7 establishes it as the durable read-once doctrine anchor the steer strings cite — the two are complementary, A9 / CH-11.)*
8. EVERY steering string emitted by a governance hook (PreToolUse `permissionDecisionReason`, SubagentStop/Stop stderr-on-exit-2, SessionStart/PostToolUse exit-0 JSON) SHALL conform to the steering charter (05-remediation-spec §2): it SHALL be a forward vector — a LOCATED defect (naming the field/actor/count and its actual value) plus the ONE legitimate move that clears it — fired at most once per turn on the one correct channel (CH-12: stderr on exit 2, the event JSON field on exit 0, never both), and on repeat it SHALL VARY/ESCALATE rather than re-inject the same string, bounded to 2–3 rungs before HANDOFF (CH-10, the anti-49×-re-injection rule). Named charter doctrines the strings inherit by reference: CH-01 (steer to the next action, never a bare verdict / single canonical source), the predictions-never-gate doctrine, the locate-the-oracle-before-any-done-claim doctrine, and CH-10 (escalate, don't re-inject). *(Reconciliation: makes the charter doctrines named, citable constraints on the reason strings — TWL-01/HGD-1; CH-12 channel discipline + CH-10 escalation.)*

---

### Requirement 14: Anti-Loopmaxxing Controls

**User Story:** As a budget owner, I want runaway loops to be impossible — hard caps, budgets, stuck-detection, and human handoff — so a hallucinating agent cannot burn the budget or accrue comprehension debt.

**Baseline block:** B13 | **PRD references:** REQ-LOOP-001..004

#### Acceptance Criteria

1. WHILE a control loop runs, THE System SHALL enforce a hard iteration cap (DEFAULT = 25 turns per Slice) and a token/cost budget per Slice.
2. IF the iteration cap OR the cost budget OR the no-progress condition is reached, THEN THE System SHALL terminate the run to HANDOFF — a terminal state distinct from COMPLETE — and SHALL NOT mark the deliverable complete. *(Z3 CHECK-3 verified.)* No-progress is operationalized as: zero coverage items flipped from `unproven` to `proven` AND zero commits produced, both conditions true simultaneously across the last N consecutive Slices (DEFAULT N = 3). *(Z3 CHECK-8a/8b verified.)*
3. IF a Slice exhausts its retry budget (DEFAULT = 3 retries), THEN THE System SHALL fail gracefully and hand off to a human rather than retrying indefinitely.
3a. IF the agent declares it is blocked on an external input it cannot itself resolve (e.g. a credential, a human decision, an upstream service), OR a pure-idle streak occurs (the agent produces no coverage progress and no tool action because it is waiting), THEN THE System SHALL treat this as a HANDOFF (`run_state.status=handoff`, exit 0) — surfacing the named blocker to a human — and SHALL NOT re-block, re-inject the prompt, or emit an idle 'standing by' turn. Idle is a HANDOFF, never a wait. *(Reconciliation 2026-06-18, audit C-IDLE-03: the ralph-loop plugin re-fired decision:block regardless of an agent-declared unresolvable external dependency, driving 24 forced 'standing by / won't fabricate' idle turns; this makes a declared external blocker / idle streak a clean surface-and-HANDOFF. The `external_blocker` flag is a loop-driver-populated run_state field, D3 precondition.)*
4. THE System SHALL trace-log agent reasoning and tool calls and retain human-readable evidence so a human can audit why the agent acted, bounding comprehension debt.
5. WHILE a Stop_Hook block is active and the run re-enters the Stop hook on the SAME no-progress / blocking condition, THE Stop_Hook SHALL emit ZERO tokens on re-entry (no re-injection of the prior reason or prompt) and SHALL escalate rather than repeat: it SHALL vary/escalate the steering message across at most `BLOCK_ESCALATION_CAP` (DEFAULT = 3, configurable via the Requirement-20 threshold registry) re-entries, and on exceeding the cap SHALL route to HANDOFF (`run_state.status=handoff`, exit 0). THE System SHALL NOT re-inject a byte-for-byte identical block reason across re-entries. *(Reconciliation 2026-06-18, audit C-LOOP-04/CH-10: the ralph-loop plugin re-injected an identical mega-prompt 49x with no escalation and no terminal; this codifies escalate-don't-re-inject with a bounded ladder that terminates to HANDOFF. The `block_streak` counter is a loop-driver-populated run_state field, D3 precondition.)*

---

### Requirement 15: Orchestration

**User Story:** As an architect, I want the inner loop run by Claude Code's own primitives and durability added only when truly needed, so redundant orchestration is avoided.

**Baseline block:** B14 | **PRD references:** REQ-ORCH-001..003

#### Acceptance Criteria

**Bounded-autonomy goal directive (REQ-ORCH-005 / A8).** A top-level steering directive (read once per session by the model, not a hook) SHALL govern self-driving:
0a. WHERE the next step is BOTH in-scope (an `in_scope == true` coverage item) AND objectively checkable (it has ≥1 machine-checkable acceptance criterion), THE System SHALL authorize the loop to self-continue without human prompting, within the Requirement-14 caps/budget.
0b. IF the loop is blocked on a dependency it cannot itself satisfy (a missing prereq, an unauthored tool, an external service, a human decision), THEN THE System SHALL emit a single `BLOCKED-ON: <dependency>` sentinel line, which is parsed into `run_state.external_blocker`, and SHALL surface-and-HANDOFF (REQ-LOOP-005) rather than idle or emit a 'standing by' continuation. THE System SHALL NOT fabricate progress to avoid the HANDOFF — anti-fabrication is paired with its terminal so honesty cannot collapse into idling.
0c. THE goal directive SHALL reference the durable invariants by short name (actor-independence, verifier-only flips, human-owned artifacts, the canonical-source pin) rather than restating them, inheriting them from the repo-root `CLAUDE.md` anchor (Requirement 13.7 / A9).

1. THE System SHALL use Claude Code subagents and hooks as the inner planner/implementer/verifier orchestrator and SHALL NOT introduce an external agent-reasoning framework for the inner loop by default.
2. WHERE crash-safe multi-hour or multi-day runs are required, THE System SHALL wrap the loop in Temporal_Inngest invoking `claude -p` as a durable step, with each tool call as a separate activity.
3. THE System SHALL keep Agent_Teams (experimental peer-to-peer) off the delivery-gating path until the feature exits experimental status and supports session resumption.

---

### Requirement 16: Durable Storage

**User Story:** As a data owner, I want traceability, run state, and evidence in one managed store, so the system's memory is durable and queryable.

**Baseline block:** B15 | **PRD references:** REQ-STORE-001..003

#### Acceptance Criteria

1. THE System SHALL persist requirements, coverage state, traceability links, Evidence_Records, and run state in a managed Postgres database.
2. WHEN evidence is captured, THE System SHALL store the artifact or a content-addressed reference and link it to the requirement ID and commit SHA.
3. THE System SHALL keep the Postgres store as the single source of truth for coverage queries, reconstructable independently of any model session.

---

### Requirement 17: Supply-Chain and Security Gates

**User Story:** As a security owner, I want agent-generated code held to SAST, secrets, and provenance gates, so autonomy does not introduce supply-chain risk.

**Baseline block:** B16 | **PRD references:** REQ-SEC-001..005

#### Acceptance Criteria

1. WHEN code is changed, THE System SHALL run Semgrep_CodeQL in CI and SHALL fail the run on any HIGH or CRITICAL severity finding.
2. IF a secret, credential, or token is detected in a diff, THEN THE System SHALL block the commit or merge.
3. WHEN an artifact is built on merge, THE System SHALL generate signed SLSA build provenance (e.g., `actions/attest-build-provenance`) verifiable via `gh attestation verify`.
4. WHILE the agent executes untrusted code, THE System SHALL run it in an isolated sandbox. *(Reconciliation 2026-06-15: DEFAULT sandbox = devcontainer locally / E2B for ephemeral CI; agent-executed code runs inside the sandbox with network egress DENIED by default and filesystem writes confined to the per-slice git worktree mounted into the sandbox — the worktree is the unit of isolation mounted in, the sandbox is the security boundary.)*
5. THE System SHALL never place credentials or secrets in prompts, spans, or URLs, and SHALL treat retrieved or model-predicted content as untrusted input data, not as instructions. THIS prohibition SHALL be enforced at the PreToolUse_Hook (exit 2 blocks a tool call whose prompt, span attributes, or URL would carry a secret), not only via an offline test. *(Reconciliation 2026-06-15: REQ-17.5 moved to a live PreToolUse prevention gate.)*

---

### Requirement 18: Human-in-the-Loop Approval

**User Story:** As the accountable human, I want to approve the complete plan before code starts and review before merge, with that approval enforced deterministically.

**Baseline block:** B17 | **PRD references:** REQ-HITL-001..003

#### Acceptance Criteria

1. IF no `plan-approved.json` approval marker exists, THEN THE PreToolUse_Hook SHALL block all implementation Write and Edit tools.
2. WHEN the validated spec and `feature_list.json` are ready, THE System SHALL present them in plan mode for human approval and missing-context injection before unlocking implementation. The free-text `notes` field of `plan-approved.json` carries the human's missing-context injection; on the next session the Initializer SHALL read `plan-approved.json.notes` and inject it into `run_state` so the Implementer's context receives it (see design.md Initializer; tasks.md). *(Reconciliation 2026-06-16: gives the "missing-context injection" SHALL an explicit consumer so the obligation is wired, not free-floating.)*
3. THE System SHALL require a human PR review (a required reviewer configured in a repository ruleset) before merge to the protected branch.
4. IF `plan-approved.json` exists BUT its `feature_list_sha` does not equal the canonical SHA-256 of the current `feature_list.json`, THEN the PreToolUse_Hook SHALL block all implementation Write/Edit/MultiEdit tools and require re-approval. *(Reconciliation 2026-06-16: the approval marker is SHA-bound to the coverage model so an approved-then-mutated `feature_list.json` cannot silently authorize implementation; Property 6 validates 7.4, 18.1, and 18.4.)*

---

### Requirement 19: Predictive Routing (Optional)

**User Story:** As a developer, I want optional predictive next-step routing to speed the agent toward the right context, without it ever overriding a gate, so I get acceleration without sacrificing the enforcement guarantee.

**Baseline block:** B18 | **PRD references:** REQ-PRED-001..003

#### Acceptance Criteria

1. WHERE predictive next-step routing is enabled, THE System SHALL inject predictions only as advisory context (e.g., via a `UserPromptSubmit` or `SessionStart` context-injection hook or an MCP retrieve tool).
2. IF a design routes a prediction into a block or allow gate decision, THEN THE System SHALL reject that design; predictions SHALL NOT emit gate decisions and gates SHALL NOT read predictions. *(Z3 CHECK-5 verified.)*
3. WHERE predictive routing is enabled, THE System SHALL tag predicted-routing spans distinctly and measure prediction acceptance and accuracy so routing can be disabled on drift. *(Implementation note: build on battle-tested primitives — Speculative Actions, semantic-router, the Claude memory tool — not on pre-product services with no shipping release as of mid-2026.)*

---

## Non-Functional Requirements

### Requirement 20: Execution Bounds and Quality Thresholds

**User Story:** As an operator, I want deterministic execution bounds and quality thresholds, so the system's performance characteristics are queryable facts, not estimates.

#### Acceptance Criteria

1. THE System SHALL enforce the following DEFAULT numeric thresholds: line coverage on touched files ≥ 85% (configurable, via pytest-cov/`coverage.json`); 0 HIGH or CRITICAL SAST findings; ≤15 minutes per Slice; iteration cap of 25 turns per Slice; retry budget of 3 per Slice; spec-completion loop cap of 7 passes; hook validator timeout of 60 seconds; telemetry export interval ≤ 5 seconds.
2. THE System SHALL treat all numeric thresholds as configurable DEFAULTs, with changes requiring explicit operator override.
3. THE System SHALL register the following additional DEFAULT thresholds in the threshold registry *(Reconciliation 2026-06-15: numeric defaults added)*:
   - **Cost/token budget** = 1,000,000 tokens per Slice (configurable); reaching it triggers the REQ-LOOP-002 HANDOFF.
   - **Reasoning-loop K** = 3 identical tool-call signatures — the repeated-action threshold for the REQ-OBS-006 / Requirement 26 reasoning-loop detector.
   - **Retry budget** = 3 per Slice — OWNER: the implementer loop; the counter lives in `run_state` (e.g., `run_state.retry_count`) and, when exhausted, hands off per REQ-LOOP-003.
   - **Vague-adjective reject-set** = {`fast`, `secure`, `scalable`, `optimized`, `efficient`, `reliable`, `performant`} (DEFAULT, configurable — the validator MAY extend it) — OWNER: the Spec_Compiler / `spec_validator.py`; enforced by Requirement 1.2 and Property 17. *(Reconciliation 2026-06-16: authoritative seven-member set registered so the implemented scanner is requirement-backed.)*
   - **Audit-log live-retention window** = 365 days (DEFAULT, configurable) — OWNER: the Delivery Owner / Operator; beyond this window verified prefixes are checkpoint-and-archived per Requirement 27.7 (the chain re-verifies across the archive boundary; mid-chain pruning is prohibited). *(Reconciliation 2026-06-16: bounds REQ-AUDIT-003 retention.)*
   - **Eval faithfulness threshold** = 0.8 (DEFAULT, configurable; operator override via the threshold registry) — OWNER: the quality owner (Requirement 9); gated by the `deepeval-gate` CI check (Requirement 30.2). *(Reconciliation 2026-06-16: the eval metric is an authoritative configurable DEFAULT, not an "e.g." illustration; satisfies the REQ-20.2 "all numeric thresholds are configurable DEFAULTs with an owner" invariant.)*
   - **Eval answer-relevancy threshold** = 0.7 (DEFAULT, configurable; operator override via the threshold registry) — OWNER: the quality owner (Requirement 9); gated by the `deepeval-gate` CI check (Requirement 30.2). *(Reconciliation 2026-06-16: authoritative configurable DEFAULT, not illustrative.)*
   - **Kill-switch flag-propagation interval** = ≤ 30 s (DEFAULT, configurable) — OWNER: the Delivery Owner / Operator (owns the flagd deployment); the affected agent capability is disabled within this interval without a process restart (REQ-CTRL-001 / Requirement 32.2). *(Reconciliation 2026-06-16: registers the kill-switch polling interval so the REQ-20.2 "all numeric DEFAULTs are configurable with an owner" invariant holds.)*

---

## Critical Invariants (Z3-Verified)

The following invariants are machine-checked by `formal_verification_merged.py` (Z3 v4.16.0, **34/34 assertions passing** — 14 core + 12 Kiro + 8 new). They are non-negotiable constraints on any implementation:

1. **Completion from facts only:** Completion is decided only by deterministic gates from verifiable facts. No prediction or self-assessment can gate. *(CHECK-5: UNSAT)*
2. **Mutually exclusive terminal states:** COMPLETE and HANDOFF are mutually exclusive terminal states. Cap/budget/no-progress terminate only to HANDOFF. *(CHECK-3: UNSAT for naive-cap → COMPLETE under unproven)*
3. **No code-write without approved plan:** No implementation Write or Edit tool may run unless `plan-approved.json` exists. *(CHECK-4f: UNSAT)*
4. **No new slice while prior slice is unproven:** A new worktree or slice cannot start while any prior-slice item is `unproven`. *(CHECK-6a: UNSAT)*
5. **Evidence schema enforced:** An item transition to `proven` with missing `output_hash` or with zero evidence fields is UNSAT. *(CHECK-7a/7c: UNSAT)*
6. **UNMAPPED blocks advancement:** Advancement to implementation while any domain-baseline item is UNMAPPED is UNSAT. *(CHECK-9a: UNSAT)*
7. **No-progress → HANDOFF only:** No-progress condition (zero items proven AND zero commits across N=3 slices) routes only to HANDOFF, never COMPLETE. *(CHECK-8b: UNSAT)*

---

## Appendix: Domain-Baseline Coverage Matrix

Every baseline block maps to ≥1 User Story and ≥1 EARS requirement. Zero `UNMAPPED` items.

| # | Baseline block | Requirement | Status |
|---|----------------|-------------|--------|
| B01 | Spec compilation | Requirement 1 (REQ-SPEC-001..004) | MAPPED |
| B02 | Proactive discovery | Requirement 2 (REQ-SPEC-010..012) | MAPPED |
| B03 | Spec-completion loop | Requirement 4 (REQ-SPEC-020..024) | MAPPED |
| B04 | Coverage model | Requirement 5 (REQ-COV-001..006) | MAPPED |
| B05 | Traceability | Requirement 6 (REQ-TRACE-001..004) | MAPPED |
| B06 | Incremental execution control | Requirement 7 (REQ-EXEC-001..005) | MAPPED |
| B07 | Wiring verification | Requirement 8 (REQ-EXEC-010..012) | MAPPED |
| B08 | Verification engine | Requirement 9 (REQ-VERIFY-001..006) | MAPPED |
| B09 | Completion gate | Requirement 10 (REQ-GATE-001..005) | MAPPED |
| B10 | Session continuity & durable state | Requirement 11 (REQ-STATE-001..004) | MAPPED |
| B11 | Observability | Requirement 12 (REQ-OBS-001..005) | MAPPED |
| B12 | Mid-flight steering | Requirement 13 (REQ-STEER-001..006) | MAPPED |
| B13 | Anti-loopmaxxing controls | Requirement 14 (REQ-LOOP-001..004) | MAPPED |
| B14 | Orchestration | Requirement 15 (REQ-ORCH-001..003) | MAPPED |
| B15 | Durable storage | Requirement 16 (REQ-STORE-001..003) | MAPPED |
| B16 | Supply-chain & security gates | Requirement 17 (REQ-SEC-001..005); extended by Requirement 31 (REQ-SEC-008) and Requirement 32 (REQ-CTRL-001) | MAPPED |
| B17 | Human-in-the-loop approval | Requirement 18 (REQ-HITL-001..003); extended by Requirement 32 (REQ-CTRL-001) | MAPPED |
| B18 | Predictive routing (OPTIONAL) | Requirement 19 (REQ-PRED-001..003) | MAPPED |
| B19 | Domain-baseline checklist sourcing | Requirement 3 (REQ-SPEC-013..015) | MAPPED |

**Addendum & NFR requirements (Reqs 20–32) — baseline traceability.** The 19 baseline blocks above remain fully MAPPED with zero UNMAPPED items. The requirements added by the Merge-Reconciliation and P3 Market-Research addenda extend those same blocks — no requirement is orphaned and no new baseline block is introduced — so the full 32-requirement set is baseline-traced:

| Requirement | Baseline block(s) | PRD references |
|-------------|-------------------|----------------|
| 20 Execution Bounds & Quality Thresholds | cross-cutting (NFR threshold registry) | — |
| 21 HANDOFF Termination Semantics | B13 | REQ-LOOP-005 |
| 22 Requirement-Amendment Versioning | B04 | REQ-COV-007 |
| 23 Resumed-State Integrity | B10 | REQ-STATE-005 |
| 24 Checklist-Approval Gate + Research Epistemic Integrity | B19 | REQ-SPEC-016, REQ-SPEC-017 |
| 25 Performance, Accessibility & UI-Completeness Verification | B08 | REQ-VERIFY-007, REQ-VERIFY-008 |
| 26 Reasoning-Loop Detection | B11 | REQ-OBS-006 |
| 27 Tamper-Evident Gate-Decision Audit Log | B09 / B11 | REQ-AUDIT-001..003 |
| 28 Capability-Role Taxonomy Extension (OPTIONAL) | B14 | REQ-ORCH-004 |
| 29 Structured Omission Declaration | B01 / B19 | REQ-SPEC-018 |
| 30 Eval-Gating in CI | B08 / B11 | REQ-EVAL-001 |
| 31 DAST Baseline Security Scan | B16 | REQ-SEC-008 |
| 32 Agent Code Kill-Switch | B16 / B17 | REQ-CTRL-001 |

---

## Merge Reconciliation Addendum — Added Requirements (canonical merge)

These requirements close gaps found in the adversarial audit against the 95-pain-point problem statement. Each is EARS-form with a `[DET]`/`[PROB]` label; logic-checkable ones cite the unified harness (`formal_verification_merged.py`, **34/34** — 14 core + 12 Kiro + 8 new).

### Requirement 21: HANDOFF Termination Semantics (correction)
**Baseline block:** B13 | **PRD references:** REQ-LOOP-005
1. IF the iteration cap, cost budget, or no-progress predicate is reached, THEN THE Stop_Hook SHALL set `run_state.status=handoff`, emit a HANDOFF summary, and ALLOW termination (exit 0). It SHALL NOT return a blocking exit code 2 for these conditions (which would force continuation). Only the unproven-items condition blocks. *(Corrects a force-continuation/infinite-block defect.)*

### Requirement 22: Requirement-Amendment Versioning
**Baseline block:** B04 | **PRD references:** REQ-COV-007
1. IF a requirement is amended after approval, THEN THE System SHALL record a `requirement_versions` row (prior text, new text, author, timestamp, rationale), re-enter the coverage item as `unproven`, and SHALL NOT permit COMPLETE while any amended item is un-reproven. *(Z3 CHECK-10a/10b.)*

### Requirement 23: Resumed-State Integrity
**Baseline block:** B10 | **PRD references:** REQ-STATE-005 | **Implementation:** `tools/state_integrity.py` (see design.md Component Inventory; tasks.md task 49)
1. IF a session resumes AND the resumed-state hash does not match the durable store's recorded hash, THEN THE System SHALL block the run from proceeding and require operator reconciliation. *(Z3 CHECK-11a/11b; guards against false/corrupted resumption.)*
2. THE SessionStart_Hook SHALL compute the resumed-state hash and write `run_state.resume_integrity_ok` (bool) without blocking, AND a NEW PreToolUse integrity-guard check SHALL BLOCK the first implementation write (exit 2) WHILE `run_state.resume_integrity_ok` is `false`, releasing only after operator reconciliation flips it true. *(Reconciliation 2026-06-15: because SessionStart cannot block, the REQ-STATE-005 enforcement gate moves to a PreToolUse integrity guard; SessionStart stays non-blocking and only computes the result.)*

### Requirement 24: Checklist-Approval Gate + Research Epistemic Integrity
**Baseline block:** B19 | **PRD references:** REQ-SPEC-016, REQ-SPEC-017
1. IF a Domain_Baseline_Checklist is in DRAFT (not human-approved), THEN it SHALL NOT be used for discovery. *(Z3 CHECK-12a/12b.)*
2. WHEN the Research_Sub_Agent drafts a checklist or any sourced claim, THEN every external claim SHALL carry a source URL, each source SHALL be labeled by authority tier (primary/standard/peer-reviewed vs blog/vendor/social), and an independent fact-check pass SHALL flag unverifiable or low-authority-only claims before human review.

### Requirement 25: Performance, Accessibility & UI-Completeness Verification
**Baseline block:** B08 | **PRD references:** REQ-VERIFY-007, REQ-VERIFY-008
1. WHEN an NFR item of subtype `performance` is verified, THE System SHALL run k6/Lighthouse against numeric budgets (e.g., p95 latency, Core Web Vitals) and attach the result as the Evidence_Record.
2. WHEN an NFR item of subtype `accessibility` is verified, THE System SHALL run axe-core and require zero WCAG-A/AA violations on covered screens.
3. THE System SHALL treat UI-screen completeness as a verification target: every declared screen/state (including empty, loading, and error states) SHALL have a behavioral test asserting it renders.

### Requirement 26: Reasoning-Loop Detection
**Baseline block:** B11 | **PRD references:** REQ-OBS-006
1. WHEN telemetry is analyzed, THE System SHALL mark reasoning spans with a custom span ATTRIBUTE (e.g. `claude.span.kind="reasoning"`) on an OTel INTERNAL span — NOT a new `SpanKind` enum value (OTel `SpanKind` is the closed enum `{INTERNAL, SERVER, CLIENT, PRODUCER, CONSUMER}`) — and SHALL flag repeated-action / reasoning-loop patterns (≥ K identical tool-call signatures, DEFAULT K = 3 per the Requirement-20 threshold registry) as a first-class signal, complementing the slice-level no-progress watchdog. *(Reconciliation 2026-06-15: REASONING is a span attribute, not a SpanKind value; K=3 default.)*

### Requirement 27: Tamper-Evident Gate-Decision Audit Log
**Baseline block:** B09/B11 | **PRD references:** REQ-AUDIT-001..003
1. THE System SHALL append every gate decision (event, tool, allow/block, reason, requirement ID, actor agent, `created_at` (timestamp)) to an append-only, hash-chained audit log where each entry stores the hash of the prior entry. *(Reconciliation 2026-06-16: the timestamp column is canonically named `created_at` across all three surfaces — requirement, DDL (design.md:1164,1170), and producer.)*
2. WHEN the audit log is verified, IF any entry's stored prior-hash does not equal the recomputed hash of the preceding entry, THEN verification SHALL fail (tamper detection).
3. THE System SHALL retain the hash-chained gate-decision log as the execution-proof complement to SLSA build provenance, so "we can prove what happened" is distinct from and additional to "the trace says what happened."
4. **Producer:** a new `tools/audit_log.py` SHALL expose `append(event, tool, decision, reason, requirement_id, actor_agent)`, and it SHALL be CALLED by `stop_hook.py`, `pre_tool_use_hook.py`, and `subagent_stop_hook.py` on every allow/block decision; `tools/audit_verify.py` SHALL recompute the chain. *(Reconciliation 2026-06-15: names the audit-log producer/verifier and its callers.)* *(Reconciliation 2026-06-16: `created_at` is DB-assigned (`DEFAULT now()`) and is therefore deliberately NOT a producer argument of `append()`; it is materialized by the database, then folded into the canonical row for hashing per criterion 27.5. The `subagent_stop_hook.py` call site spans BOTH its evidence-schema decision (design.md:217) AND its omission-declaration-guard block decision (design.md:218) — i.e. three hook files / four decision points.)*
5. **Hash-chain canonical form:** the genesis entry SHALL use `prev_hash = sha256("")` (the empty-string digest) as a documented sentinel; the canonical form SHALL be the deterministic JSON of `(seq, event_name, tool_name, decision, reason, requirement_id, actor_agent, created_at)`; `entry_hash = sha256(canonical_row || prev_hash)` and SHALL INCLUDE `seq` and `created_at`. *(Reconciliation 2026-06-15: pins the chaining algorithm and genesis sentinel.)*
6. **Verification trigger:** chain verification SHALL run as a REQUIRED CI status check at merge AND on-demand via `tools/audit_verify.py`. *(Reconciliation 2026-06-15: dual trigger — CI-gated at merge plus on-demand.)*
7. **Retention & archival:** THE System SHALL retain the live `gate_audit_log` for a minimum window (DEFAULT = 365 days, configurable per the Requirement-20 threshold registry; OWNER: the Delivery Owner / Operator). Because the log is an append-only hash chain, the middle SHALL NOT be pruned in place; instead, verified segments older than the live window SHALL be checkpoint-and-archived — a contiguous verified prefix is exported to durable cold storage, recording that prefix's tip `entry_hash` as the archive segment's tip, and the live chain continues unbroken (the next live entry's `prev_hash` still equals the archived tip, so `audit_verify.py` re-verifies *across* the archive boundary). Archived segments SHALL be stored immutably (write-once) and remain hash-verifiable end-to-end. IF operating v1 without archival, THEN unbounded append-only retention is the accepted DEFAULT and pruning is prohibited. *(Reconciliation 2026-06-16: operationalizes "SHALL retain" — bounds the live window, defines a chain-compatible archive whose boundary preserves verifiability, and forbids mid-chain pruning; wired as a subtask under task 52. Mirror near design.md:1156–1177.)*
8. **Scope of the hash chain:** THE hash-chained `gate_audit_log` captures Claude Code hook gate decisions (the `stop_hook.py` / `pre_tool_use_hook.py` / `subagent_stop_hook.py` allow/block decisions of criterion 27.4). CI-status-check gates — `deepeval-gate`, `zap-baseline`, `coverage-gate`, `secrets-scan`, and the `audit-chain-verify` check itself — are recorded via GitHub check-run history and SLSA provenance rather than the hook audit log, so the "we can prove what happened" chain has no silent hole: each gate decision is captured by exactly one of the two execution-proof substrates (hook hash chain OR check-run/SLSA history). *(Reconciliation 2026-06-16: closes the deepeval-gate-vs-audit-log scope ambiguity by stating where each gate class is recorded; if a future `deepeval-gate` block must enter the hash chain it would be added to the criterion 27.4 caller list.)*

### Requirement 28: Capability-Role Taxonomy Extension (Optional)
**Baseline block:** B14 | **PRD references:** REQ-ORCH-004
1. WHERE a project requires roles beyond planner/implementer/verifier/research, THE System SHALL support additional bounded subagent roles — design, platform, reliability — each with an explicit permission scope; none SHALL have verifier write access. *(OPTIONAL — v1 is not over-built.)*

---

## P3 Market-Research Addendum — Added Requirements (Tier-1 industry-standard enrichment)

These requirements add four Tier-1 capabilities confirmed by the P3 deep-research phase (June 2026). Each was independently verified for fit against the Claude Code substrate and this architecture before inclusion. Two candidates (Pact contract testing, runtime structured-output enforcement) produced zero verified Tier-1 evidence for this substrate and are explicitly deferred (see Out-of-scope section).

### Requirement 29: Structured Omission Declaration
**Baseline block:** B01/B19 | **PRD references:** REQ-SPEC-018
1. WHEN a subagent (initializer, research, verifier) completes a discovery, research, or verification pass, THEN its output SHALL include a non-null `omission_declaration` field listing, by EARS scenario category (Primary / Alternate / Exception / Recovery / Non-Functional / Edge-Case), every scenario class the subagent did NOT cover, using a `[Gap]` marker for each omitted class. *(GitHub Spec-Kit pattern — machine-checkable "unit test for requirements writing".)* *(Reconciliation 2026-06-16: the IMPLEMENTER subagent is EXEMPT from both the Evidence_Record field check and the omission-declaration check at SubagentStop — it produces a commit, not evidence, and hands off to the Verifier (REQ-VERIFY-005 / 9.5). The "EACH subagent output type" of criterion 29.3 therefore scopes to the evidence-/declaration-producing types (initializer, research, verifier); the implementer→verifier handoff carries no `omission_declaration`. This is mirrored in `subagent_stop_hook.py` (task 8.1) and the `omission_guard` component (design.md:148, design.md:218), whose guard fires only on initializer/research/verifier results.)*
2. THE SubagentStop hook SHALL reject any subagent result whose `omission_declaration` field is absent or null, with exit 2. *(Z3 CHECK-13a/13b; Property 30.)* *(Reconciliation 2026-06-16: the machine-checked gate enforces PRESENCE / non-null ONLY — CHECK-13a/13b and Property 30 model a single boolean `omissionDeclNull`. The per-category `[Gap]` enumeration of criterion 29.1, Primary/Alternate/Exception/Recovery/Non-Functional/Edge-Case, is a non-gating authoring convention reviewed by a human at SubagentStop, NOT a harness-checked constraint; so the "machine-checkable" claim is scoped to non-null presence, not to per-category completeness.)*
3. THE JSON schema for each subagent output type SHALL include `omission_declaration` as a required, non-nullable field. *(Reconciliation 2026-06-16: empty-but-non-null is intentionally ACCEPTED by the omission gate — `""`, `{}`, `[]` pass 29.2/29.3, which check absence/null ONLY. This deliberately diverges from the Evidence_Record sibling gate (Requirement 5.6), which rejects "absent or empty"; the divergence is by design because the per-category content is a non-gating authoring convention (see 29.2 note) and the harness models only `omissionDeclNull`. Tightening to "absent, null, or empty" would require a new harness predicate and is out of scope for the frozen 34-check count.)*

### Requirement 30: Eval-Gating in CI
**Baseline block:** B08/B11 | **PRD references:** REQ-EVAL-001
1. THE System SHALL include a DeepEval eval-gating step in CI using the pytest-native `assert_test()` API for LLM output quality assertions.
2. WHEN a CI run includes LLM output evaluation, THEN the eval step SHALL gate on the configured DEFAULT metric thresholds (faithfulness ≥ 0.8, answer relevancy ≥ 0.7 — registered in the Requirement-20 threshold registry, operator-overridable) using DeepEval `assert_test()`, failing the build if any threshold is not met. The evaluable output is sourced from a versioned golden-set fixture under `tests/eval/` (each case supplying the DeepEval `LLMTestCase` `input` / `actual_output` / `retrieval_context` fields), seeded from Verifier-run evidence; the dataset source is itself version-controlled so the eval is reproducible. *(Reconciliation 2026-06-16: names the producer/dataset of the RAG-style metric tuples and drops the "e.g." so 0.8/0.7 are authoritative DEFAULTs, not illustrations.)*
3. THE eval step SHALL run as a REQUIRED CI status check at merge (`deepeval-gate` check name). When a CI run contains NO LLM output to evaluate (no fixture case applies), the `deepeval-gate` check SHALL pass vacuously (green with zero cases asserted) rather than block — so the unconditional REQUIRED status is never blocking-with-nothing-to-evaluate, and the WHEN-guard of criterion 30.2 governs only runs that DO include evaluable output. *(Fits existing pytest/Hypothesis stack; promptfoo deferred to Phase 3+.)* *(Reconciliation 2026-06-16: reconciles the criterion-2 WHEN-guard with the unconditional REQUIRED gate by defining the empty-evaluation case as a vacuous pass.)*

### Requirement 31: DAST Baseline Security Scan
**Baseline block:** B16 | **PRD references:** REQ-SEC-008
*(Reconciliation 2026-06-16: REQ-SEC-008 is a `[DET]` CI-gate obligation enforced by the `zap-baseline` REQUIRED status check; it deliberately carries NO Z3 Property/CHECK and is OUTSIDE the `formal_verification_merged.py` formal-verification harness scope — as is implicitly true for `secrets-scan`, `coverage-gate`, and `deepeval-gate`. The absence of a Property/CHECK is documented intent, not an oversight. Baseline block corrected from B15 (Durable storage) to B16 (Supply-chain & security gates), the correct home for a DAST scan.)*
1. THE System SHALL run an OWASP ZAP baseline passive scan on every PR via `zaproxy/action-baseline@v0.12.0` with `fail_action: true`.
2. THE DAST scan SHALL be registered as a REQUIRED CI status check at merge (`zap-baseline` check name).
3. Active/full ZAP scans are OUT OF SCOPE for v1; only the baseline passive scan is required. *(Rationale: baseline scan covers passive discovery with zero false-positive risk from active probing; active scan added post-v1 when an authenticated target exists.)*

### Requirement 32: Agent Code Kill-Switch
**Baseline block:** B16/B17 | **PRD references:** REQ-CTRL-001
1. THE System SHALL implement an agent-capability kill-switch using OpenFeature + flagd (Apache 2.0, self-hosted, CNCF Incubating).
2. WHEN a kill-switch flag is set, THEN the affected agent capability SHALL be disabled within the polling interval (≤ 30 seconds) WITHOUT requiring a process restart.
3. THE flagd server SHALL be self-hosted (no SaaS dependency), SHALL expose the OpenFeature SDK interface, and SHALL support near-real-time flag updates via file-based or gRPC provider.
4. THE System SHALL restrict kill-switch flag toggles to the Delivery Owner / Operator role; each toggle SHALL be authenticated and recorded. *(Reconciliation 2026-06-16: binds the B17 human-in-the-loop mapping to a named accountable actor — analogous to plan-approval being bound to `plan-approved.json` written by a named human — so a flag flip is not an anonymous action.)*
5. WHEN a kill-switch flag is set or cleared, THE System SHALL append a `gate_audit_log` entry (event, actor agent/operator, decision, reason, requirement ID, `created_at`) via `tools/audit_log.append(...)` AND emit an OTel gate-decision event to the same trace endpoint as other gate decisions, so the toggle is in the tamper-evident hash chain (REQ-AUDIT-001..003 / Requirement 27) and observable (REQ-OBS-003 / Requirement 12.3). *(Reconciliation 2026-06-16: wires the kill-switch toggle into the audit/observability substrates; mirrored in design.md by listing the kill-switch toggle among `audit_log.append` callers in the Kill-Switch subsection.)*

### Added Critical Invariants (Z3-Verified, unified harness)
8. **Amendment monotonicity:** an amended-but-not-reproven requirement cannot be COMPLETE. *(CHECK-10a UNSAT; CHECK-10b SAT.)*
9. **Resumed-state integrity:** a resume with a state-hash mismatch cannot proceed. *(CHECK-11a UNSAT; CHECK-11b SAT.)*
10. **Checklist-approval-before-use:** a DRAFT checklist cannot be used for discovery. *(CHECK-12a UNSAT; CHECK-12b SAT.)*

**Cross-reference to the tasks/design correctness properties** *(Reconciliation 2026-06-15: the locally-numbered invariants 8/9/10 above map to the canonical Properties 25–29 and CHECK-10..12 used in tasks.md / design.md)*:

| Local invariant | Correctness Property | Z3 group | Requirement |
|-----------------|----------------------|----------|-------------|
| 8 (amendment monotonicity) | Property 25 | CHECK-10a/10b | Requirement 22 |
| 9 (resumed-state integrity) | Property 26 | CHECK-11a/11b | Requirement 23 |
| 10 (checklist-approval-before-use) | Property 27 | CHECK-12a/12b | Requirement 24.1 |
| — (audit-log tamper-evidence) | Property 28 | — (runtime/CI, no Z3: `audit_verify.py` + Property 28 PBT) | Requirement 27 |
| — (research authority / epistemic integrity) | Property 29 | — | Requirement 24.2 |
| — (omission-declaration gate) | Property 30 | CHECK-13a/13b | Requirement 29 |
| — (eval-gating in CI) | — (no Z3 Property — Property 30 belongs to Requirement 29, not this row) | — (runtime/CI, no Z3) | Requirement 30 (verified by the `deepeval-gate` named CI check) |

*(Reconciliation 2026-06-16: Requirement 30 / REQ-EVAL-001 carries NO Z3 Property or CHECK; its named verification tool is the `deepeval-gate` REQUIRED CI status check, satisfying the "every new requirement carries a Z3 check OR a named verification tool" traceability rule. This row also disambiguates the Property-30-vs-Requirement-30 collision: Property 30 verifies Requirement 29's omission gate, not Requirement 30. A `deepeval-gate` smoke/integration test — asserting the build fails when a metric is below threshold — is wired in tasks.md, since the harness stops at CHECK-13b and no PBT covers REQ-EVAL-001.)*

The full correctness set is **32 properties (Properties 1–24 plus 25–32)**; the merged harness `formal_verification_merged.py` self-counts to **34 assertions (14 core + 12 Kiro + 8 new)**. *(Reconciliation 2026-06-16: Properties 31 (perf/a11y/ui-screen evidence, REQ-VERIFY-007/008) and 32 (CI secrets diff-scan blocks merge, REQ-17.2) are PBT/CI-verified with no Z3 oracle — they close prior wiring gaps but do not change the frozen 34-check harness count.)*

### Out-of-scope (explicit, deferred with rationale)
The plan is **five required phases (0–4) plus two optional phases (5–6)**. Deferred: predictive routing (optional Phase 6, off-gate); Temporal/Inngest (optional Phase 5); Agent Teams (until non-experimental); full EU AI Act legal conformity packaging (substrate provided via REQ-AUDIT-* + SLSA); deductive correctness proof of generated code (Z3 proves the logic model only).

**P3 market-research deferrals (zero Tier-1 evidence for this substrate, post-v1):**
- **Pact consumer-driven contract testing** — no verified evidence of Pact fit with Claude Code hook/subagent boundaries; contract testing at the LLM output layer is an open research area with no established standard. Revisit when a stable cross-agent contract testing pattern exists.
- **Runtime structured-output schema enforcement (Pydantic/BAML)** — the SubagentStop schema-validation gate (REQ-COV-006) already enforces Evidence_Record structure at the hook layer; additional Pydantic/BAML enforcement at the call site adds coupling without closing a gap not already gated. Revisit if schema drift between call sites and gate layer is observed in practice.
