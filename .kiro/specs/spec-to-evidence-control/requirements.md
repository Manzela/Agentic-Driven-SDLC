# Requirements Document

## Introduction

The Spec-to-Evidence Coverage Control System is an autonomous agentic software-delivery control plane that runs on the Claude Code substrate. Its purpose is to minimize human micro-steering by converting product intent into a traceable, machine-verifiable coverage model that governs agent execution and rejects incomplete delivery.

The governing invariant: **deterministic gates — Claude Code hooks, CI, OPA — decide whether delivery is complete, computed solely from verifiable facts. Model self-assessment and probabilistic predictions only inform; they never gate.**

The system is structured around 19 domain-baseline capability blocks (B01–B19) and is specified by **32 numbered requirements** (Requirement 1–32 — 20 original plus 12 added: Req 21–28 in the Merge Reconciliation Addendum, Req 29–32 in the P3 Market-Research Addendum), verified by a unified Z3 formal-verification harness (`formal_verification_merged.py`, **34/34 machine-checked assertions passing** — groups: 14 core (CHECK-1..5c) + 12 Kiro (CHECK-6a..9c) + 8 new (CHECK-10a..13b)). The minimum viable spine (Phase 0) consists of: `feature_list.json` + Stop hook + independent verifier subagent + git worktrees + GitHub required status check + Playwright behavioral proof. *(Reconciliation 2026-06-15: the deprecated `formal_verification.py` and its "21 checks" figure are never cited; the merged harness self-counts to 34.)*

The delivery plan comprises **five required phases (0–4) plus two optional phases (5–6)**. Out of scope for v1: Agent Teams peer-to-peer (experimental); Temporal/Inngest durable outer loop (optional Phase 5); predictive next-step routing (optional Phase 6, off-gate); full EU AI Act legal conformity packaging; and deductive correctness proof of generated code. NOTE: performance AND accessibility verification are now IN scope via REQ-VERIFY-007/008 (this corrects the prior out-of-scope exclusion).

---

## Glossary

- **System**: The Spec-to-Evidence Coverage Control System as a whole.
- **Spec_Compiler**: The component responsible for transforming product intent into atomic, individually-testable requirements with IDs and acceptance criteria.
- **Coverage_Model**: The machine-readable map of every required feature/behavior/NFR, embodied in `feature_list.json`, that defaults every item to `unproven`.
- **Verifier**: The independent evaluator subagent that performs completion verification. It has no write access to the implementation and does not verify its own output.
- **Completion_Gate**: The deterministic enforcement layer (Stop hook + OPA/Conftest CI check + GitHub required status check) that blocks delivery from being declared complete while any in-scope requirement is `unproven`.
- **PreToolUse_Hook**: The Claude Code `PreToolUse` hook — the sole true prevention gate (exit 2 blocks before execution). Not to be confused with `PostToolUse`, which cannot undo an already-executed action.
- **Stop_Hook**: The Claude Code `Stop` hook that blocks agent termination when the coverage model contains any `unproven` in-scope item.
- **SubagentStop_Hook**: The Claude Code `SubagentStop` hook that validates evidence schema before accepting a subagent's result.
- **PostToolUse_Hook**: The Claude Code `PostToolUse` hook — a next-turn forcing function only; it cannot undo an already-executed action.
- **PreCompact_Hook**: The Claude Code `PreCompact` hook that checkpoints progress before context compaction.
- **SessionStart_Hook**: The Claude Code `SessionStart` hook that restores run state at the start of a session.
- **feature_list.json**: The canonical, version-controlled coverage-model file. Every in-scope item appears here with type, status, dependencies, acceptance criteria, and evidence.
- **Evidence_Record**: A structured record with exactly four required fields: `test_file`, `test_name`, `output_hash`, `collected_at`. An item cannot transition to `proven` without all four fields present.
- **Slice**: A bounded unit of implementation work, targeting ≤15 minutes / ≤1 feature, implemented in a dedicated git worktree and resulting in one atomic commit.
- **EARS**: Easy Approach to Requirements Syntax — the requirements-expression standard used throughout. Patterns: Ubiquitous, Event-driven, State-driven, Unwanted behaviour, Optional, Complex.
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
- **plan-approved.json**: The approval marker file whose presence is required before any implementation Write/Edit tool is permitted.
- **Postgres**: The managed relational database used as the durable store for requirements, coverage state, traceability links, evidence, and run state.
- **Temporal_Inngest**: Optional durable-execution engines (Temporal or Inngest) for wrapping the inner loop in crash-safe multi-hour/multi-day runs. Off by default.
- **Agent_Teams**: The experimental Claude Code peer-to-peer multi-agent feature. Kept off the delivery-gating path until it exits experimental status.
- **Semgrep_CodeQL**: The SAST tools used in CI to detect HIGH/CRITICAL security findings in changed code.
- **Playwright**: The E2E test framework used to produce behavioral proofs (captured traces/screenshots) as evidence.

---

## Requirements

### Requirement 1: Spec Compilation

**User Story:** As a product owner, I want terse intent compiled into atomic, individually-testable requirements with unique IDs and acceptance criteria, so the agent and I share one machine-checkable definition of scope.

**Baseline block:** B01 | **PRD references:** REQ-SPEC-001..004

#### Acceptance Criteria

1. THE Spec_Compiler SHALL compile product intent into atomic requirements, each with a unique ID, an EARS-pattern statement, a priority field, and ≥1 machine-checkable acceptance criterion.
2. IF a candidate requirement contains a non-deterministic adjective (e.g., "fast", "secure", "scalable", "optimized") without a quantified numeric bound, THEN THE Spec_Compiler SHALL reject it and require a quantified criterion before acceptance.
3. THE Spec_Compiler SHALL persist compiled requirements as version-controlled artifacts in the repository, not in model context alone.
4. WHEN a requirement is authored or modified, THE Spec_Compiler SHALL validate it against the EARS schema and assign exactly one of the five EARS patterns.

---

### Requirement 2: Proactive Discovery

**User Story:** As a founder with limited context, I want the system to infer the implied, industry-standard features I did not enumerate, so a complete competitive product is specified without me hand-listing every micro-feature.

**Baseline block:** B02 | **PRD references:** REQ-SPEC-010..012

#### Acceptance Criteria

1. THE System SHALL expand product intent against a curated Domain_Baseline_Checklist for the detected product class and propose implied requirements for each baseline item.
2. IF any Domain_Baseline_Checklist item has zero proposed requirements after discovery, THEN THE System SHALL flag that item `UNMAPPED` and SHALL NOT advance to implementation.
3. WHILE proactive discovery is active, THE System SHALL present every inferred requirement for human confirmation and SHALL mark inferred-vs-stated provenance on each requirement.

---

### Requirement 3: Domain-Baseline Checklist Sourcing

**User Story:** As a product owner, I want domain-baseline checklists to be researched, version-controlled, and auditably linked to coverage, so discovery quality is not dependent on ad-hoc model knowledge.

**Baseline block:** B19 | **PRD references:** REQ-SPEC-013..015

#### Acceptance Criteria

1. WHEN a new product class is encountered for the first time, THE System SHALL run a Research_Sub_Agent that queries competitive analysis, industry standards, and open-source reference implementations to draft a Domain_Baseline_Checklist for that product class, and SHALL present the draft for human review before use.
2. THE System SHALL persist Domain_Baseline_Checklists as version-controlled artifacts in the repository, named by product class, so checklists accumulate across projects and do not need to be re-derived from scratch.
3. WHEN a Domain_Baseline_Checklist is used, THE System SHALL record which checklist version was used and link it to `feature_list.json` so the derivation is auditable.

---

### Requirement 4: Spec-Completion Loop

**User Story:** As an operator, I want spec elaboration to run until the spec is provably free of contradictions, ambiguities, and gaps — bounded so it cannot loop forever or declare itself done to escape — so I get a complete spec without endless token burn.

**Baseline block:** B03 | **PRD references:** REQ-SPEC-020..024

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
4. WHEN a file edit completes, THE PostToolUse_Hook SHALL run lint, SAST, and wiring checks and, on failure, SHALL return the specific errors to the agent for correction on its next turn. (THE PostToolUse_Hook SHALL NOT be relied upon to undo the edit; see the PreToolUse_Hook for prevention.)
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
3. IF a tool call targets a protected artifact (tests, coverage-model schema, CI config) or a destructive operation, THEN THE PreToolUse_Hook command-type hook SHALL block it.
4. THE System SHALL use command-type hooks for hard policy enforcement (which fail closed) and SHALL NOT use HTTP or MCP hooks for hard policy (which fail open).
5. THE System SHALL honor the hook exit-code contract: exit 0 = proceed, exit 2 = blocking error fed to the model via stderr, any non-zero exit other than 2 = non-blocking (exit 1 does NOT block).
6. No gate decision SHALL read a probabilistic prediction; gate outcomes SHALL depend only on verifiable facts. *(Z3 CHECK-5 verified: a differing prediction cannot produce a differing gate decision.)*

---

### Requirement 14: Anti-Loopmaxxing Controls

**User Story:** As a budget owner, I want runaway loops to be impossible — hard caps, budgets, stuck-detection, and human handoff — so a hallucinating agent cannot burn the budget or accrue comprehension debt.

**Baseline block:** B13 | **PRD references:** REQ-LOOP-001..004

#### Acceptance Criteria

1. WHILE a control loop runs, THE System SHALL enforce a hard iteration cap (DEFAULT = 25 turns per Slice) and a token/cost budget per Slice.
2. IF the iteration cap OR the cost budget OR the no-progress condition is reached, THEN THE System SHALL terminate the run to HANDOFF — a terminal state distinct from COMPLETE — and SHALL NOT mark the deliverable complete. *(Z3 CHECK-3 verified.)* No-progress is operationalized as: zero coverage items flipped from `unproven` to `proven` AND zero commits produced, both conditions true simultaneously across the last N consecutive Slices (DEFAULT N = 3). *(Z3 CHECK-8a/8b verified.)*
3. IF a Slice exhausts its retry budget (DEFAULT = 3 retries), THEN THE System SHALL fail gracefully and hand off to a human rather than retrying indefinitely.
4. THE System SHALL trace-log agent reasoning and tool calls and retain human-readable evidence so a human can audit why the agent acted, bounding comprehension debt.

---

### Requirement 15: Orchestration

**User Story:** As an architect, I want the inner loop run by Claude Code's own primitives and durability added only when truly needed, so redundant orchestration is avoided.

**Baseline block:** B14 | **PRD references:** REQ-ORCH-001..003

#### Acceptance Criteria

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
2. WHEN the validated spec and `feature_list.json` are ready, THE System SHALL present them in plan mode for human approval and missing-context injection before unlocking implementation.
3. THE System SHALL require a human PR review (a required reviewer configured in a repository ruleset) before merge to the protected branch.

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
| B16 | Supply-chain & security gates | Requirement 17 (REQ-SEC-001..005) | MAPPED |
| B17 | Human-in-the-loop approval | Requirement 18 (REQ-HITL-001..003) | MAPPED |
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
| 31 DAST Baseline Security Scan | B15 | REQ-SEC-008 |
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
**Baseline block:** B10 | **PRD references:** REQ-STATE-005
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
1. THE System SHALL append every gate decision (event, tool, allow/block, reason, requirement ID, actor agent, timestamp) to an append-only, hash-chained audit log where each entry stores the hash of the prior entry.
2. WHEN the audit log is verified, IF any entry's stored prior-hash does not equal the recomputed hash of the preceding entry, THEN verification SHALL fail (tamper detection).
3. THE System SHALL retain the hash-chained gate-decision log as the execution-proof complement to SLSA build provenance, so "we can prove what happened" is distinct from and additional to "the trace says what happened."
4. **Producer:** a new `tools/audit_log.py` SHALL expose `append(event, tool, decision, reason, requirement_id, actor_agent)`, and it SHALL be CALLED by `stop_hook.py`, `pre_tool_use_hook.py`, and `subagent_stop_hook.py` on every allow/block decision; `tools/audit_verify.py` SHALL recompute the chain. *(Reconciliation 2026-06-15: names the audit-log producer/verifier and its callers.)*
5. **Hash-chain canonical form:** the genesis entry SHALL use `prev_hash = sha256("")` (the empty-string digest) as a documented sentinel; the canonical form SHALL be the deterministic JSON of `(seq, event_name, tool_name, decision, reason, requirement_id, actor_agent, created_at)`; `entry_hash = sha256(canonical_row || prev_hash)` and SHALL INCLUDE `seq` and `created_at`. *(Reconciliation 2026-06-15: pins the chaining algorithm and genesis sentinel.)*
6. **Verification trigger:** chain verification SHALL run as a REQUIRED CI status check at merge AND on-demand via `tools/audit_verify.py`. *(Reconciliation 2026-06-15: dual trigger — CI-gated at merge plus on-demand.)*

### Requirement 28: Capability-Role Taxonomy Extension (Optional)
**Baseline block:** B14 | **PRD references:** REQ-ORCH-004
1. WHERE a project requires roles beyond planner/implementer/verifier/research, THE System SHALL support additional bounded subagent roles — design, platform, reliability — each with an explicit permission scope; none SHALL have verifier write access. *(OPTIONAL — v1 is not over-built.)*

---

## P3 Market-Research Addendum — Added Requirements (Tier-1 industry-standard enrichment)

These requirements add four Tier-1 capabilities confirmed by the P3 deep-research phase (June 2026). Each was independently verified for fit against the Claude Code substrate and this architecture before inclusion. Two candidates (Pact contract testing, runtime structured-output enforcement) produced zero verified Tier-1 evidence for this substrate and are explicitly deferred (see Out-of-scope section).

### Requirement 29: Structured Omission Declaration
**Baseline block:** B01/B19 | **PRD references:** REQ-SPEC-018
1. WHEN a subagent (initializer, research, verifier) completes a discovery, research, or verification pass, THEN its output SHALL include a non-null `omission_declaration` field listing, by EARS scenario category (Primary / Alternate / Exception / Recovery / Non-Functional / Edge-Case), every scenario class the subagent did NOT cover, using a `[Gap]` marker for each omitted class. *(GitHub Spec-Kit pattern — machine-checkable "unit test for requirements writing".)*
2. THE SubagentStop hook SHALL reject any subagent result whose `omission_declaration` field is absent or null, with exit 2. *(Z3 CHECK-13a/13b; Property 30.)*
3. THE JSON schema for each subagent output type SHALL include `omission_declaration` as a required, non-nullable field.

### Requirement 30: Eval-Gating in CI
**Baseline block:** B08/B11 | **PRD references:** REQ-EVAL-001
1. THE System SHALL include a DeepEval eval-gating step in CI using the pytest-native `assert_test()` API for LLM output quality assertions.
2. WHEN a CI run includes LLM output evaluation, THEN the eval step SHALL gate on configured metric thresholds (e.g., faithfulness ≥ 0.8, answer relevancy ≥ 0.7) using DeepEval `assert_test()`, failing the build if any threshold is not met.
3. THE eval step SHALL run as a REQUIRED CI status check at merge (`deepeval-gate` check name). *(Fits existing pytest/Hypothesis stack; promptfoo deferred to Phase 3+.)*

### Requirement 31: DAST Baseline Security Scan
**Baseline block:** B15 | **PRD references:** REQ-SEC-008
1. THE System SHALL run an OWASP ZAP baseline passive scan on every PR via `zaproxy/action-baseline@v0.12.0` with `fail_action: true`.
2. THE DAST scan SHALL be registered as a REQUIRED CI status check at merge (`zap-baseline` check name).
3. Active/full ZAP scans are OUT OF SCOPE for v1; only the baseline passive scan is required. *(Rationale: baseline scan covers passive discovery with zero false-positive risk from active probing; active scan added post-v1 when an authenticated target exists.)*

### Requirement 32: Agent Code Kill-Switch
**Baseline block:** B16/B17 | **PRD references:** REQ-CTRL-001
1. THE System SHALL implement an agent-capability kill-switch using OpenFeature + flagd (Apache 2.0, self-hosted, CNCF Incubating).
2. WHEN a kill-switch flag is set, THEN the affected agent capability SHALL be disabled within the polling interval (≤ 30 seconds) WITHOUT requiring a process restart.
3. THE flagd server SHALL be self-hosted (no SaaS dependency), SHALL expose the OpenFeature SDK interface, and SHALL support near-real-time flag updates via file-based or gRPC provider.

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
| — (audit-log tamper-evidence) | Property 28 | CHECK (audit chain) | Requirement 27 |
| — (research authority / epistemic integrity) | Property 29 | — | Requirement 24.2 |
| — (omission-declaration gate) | Property 30 | CHECK-13a/13b | Requirement 29 |

The full correctness set is **30 properties (Properties 1–24 plus new 25–30)**; the merged harness `formal_verification_merged.py` self-counts to **34 assertions (14 core + 12 Kiro + 8 new)**.

### Out-of-scope (explicit, deferred with rationale)
The plan is **five required phases (0–4) plus two optional phases (5–6)**. Deferred: predictive routing (optional Phase 6, off-gate); Temporal/Inngest (optional Phase 5); Agent Teams (until non-experimental); full EU AI Act legal conformity packaging (substrate provided via REQ-AUDIT-* + SLSA); deductive correctness proof of generated code (Z3 proves the logic model only).

**P3 market-research deferrals (zero Tier-1 evidence for this substrate, post-v1):**
- **Pact consumer-driven contract testing** — no verified evidence of Pact fit with Claude Code hook/subagent boundaries; contract testing at the LLM output layer is an open research area with no established standard. Revisit when a stable cross-agent contract testing pattern exists.
- **Runtime structured-output schema enforcement (Pydantic/BAML)** — the SubagentStop schema-validation gate (REQ-COV-006) already enforces Evidence_Record structure at the hook layer; additional Pydantic/BAML enforcement at the call site adds coupling without closing a gap not already gated. Revisit if schema drift between call sites and gate layer is observed in practice.
