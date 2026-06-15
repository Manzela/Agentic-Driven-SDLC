# Requirements Document

## Introduction

The Spec-to-Evidence Coverage Control System is an autonomous agentic software-delivery control plane that runs on the Claude Code substrate. Its purpose is to minimize human micro-steering by converting product intent into a traceable, machine-verifiable coverage model that governs agent execution and rejects incomplete delivery.

The governing invariant: **deterministic gates — Claude Code hooks, CI, OPA — decide whether delivery is complete, computed solely from verifiable facts. Model self-assessment and probabilistic predictions only inform; they never gate.**

The system is structured around 19 domain-baseline capability blocks (B01–B19), verified by a Z3 formal-verification harness (34/34 assertions passing). The minimum viable spine (Phase 0) consists of: `feature_list.json` + Stop hook + independent verifier subagent + git worktrees + GitHub required status check + Playwright behavioral proof.

Out of scope for this spec: Agent Teams peer-to-peer (experimental), the Temporal/Inngest outer loop and predictive routing (optional Phases 5–6), and load/performance testing of the control plane itself (the system's own throughput/latency under load). Note: verifying the *performance and accessibility NFRs of agent-built features* IS in scope — see Requirement 9 criteria 7–8 (REQ-VERIFY-007/008).

**Deferred with rationale (candidates for Phase 1+):** eval-gating-in-CI, consumer-driven contract testing (Pact), runtime structured-output schema enforcement (Pydantic/BAML), DAST/OWASP ZAP, and progressive-delivery feature-flag kill-switches. These are net-new capabilities surfaced by market research; they are deferred (not silently dropped) and may be promoted into a later phase. The native `/security-review` pass is adopted now (low cost) while full DAST is deferred.

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
- **EARS**: Easy Approach to Requirements Syntax — the requirements-expression standard used throughout. Patterns: Ubiquitous, Event-driven, State-driven, Unwanted, Optional.
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

**Baseline block:** B19 | **PRD references:** REQ-SPEC-013..016

#### Acceptance Criteria

1. WHEN a new product class is encountered for the first time, THE System SHALL run a Research_Sub_Agent that queries competitive analysis, industry standards, and open-source reference implementations to draft a Domain_Baseline_Checklist for that product class, and SHALL present the draft for human review before use.
2. THE System SHALL persist Domain_Baseline_Checklists as version-controlled artifacts in the repository, named by product class, so checklists accumulate across projects and do not need to be re-derived from scratch.
3. WHEN a Domain_Baseline_Checklist is used, THE System SHALL record which checklist version was used and link it to `feature_list.json` so the derivation is auditable.
4. IF a Domain_Baseline_Checklist is in DRAFT state (no `approved_at`), THEN THE PreToolUse_Hook SHALL block its use for proactive discovery; a checklist SHALL be used for discovery only after human approval. *(REQ-SPEC-016; Z3 CHECK-12a/12b verified: DRAFT ∧ used-for-discovery is UNSAT.)*

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
6. IF the spec-completion pass cap (criterion 4.4) is reached WHILE `violation_count > 0`, THEN the HANDOFF of criterion 4.4 (exit 0) SHALL take precedence over the criterion 4.2 block (exit 2); the pass-cap HANDOFF resolves the otherwise-conflicting exit codes (lex specialis). *(REQ-SPEC-021.)*

---

### Requirement 5: Coverage Model

**User Story:** As a delivery lead, I want one machine-readable map of every required feature, behavior, and NFR that defaults to "unproven," so completeness is a queryable fact rather than a claim.

**Baseline block:** B04 | **PRD references:** REQ-COV-001..007

#### Acceptance Criteria

1. THE System SHALL maintain `feature_list.json` in which every item has an ID, a type ∈ {functional, NFR, WIRING}, a dependencies list, acceptance criteria, and a status field defaulting to `unproven`.
2. IF a tool action would delete, reorder, or modify an existing coverage item's identity, THEN THE PreToolUse_Hook SHALL block it; status transitions SHALL only proceed in the direction `unproven → proven`.
3. WHEN an item is set to `proven`, THE System SHALL require an attached Evidence_Record containing exactly four required fields: `test_file` (path to the test), `test_name` (unique test identifier), `output_hash` (content-addressed hash of the test output), and `collected_at` (ISO-8601 timestamp); the transition SHALL be rejected if any of the four fields is absent.
4. THE System SHALL represent architectural WIRING obligations and NFR items as first-class coverage items in `feature_list.json`, not as code comments or informal afterthoughts.
5. WHILE any in-scope item is `unproven`, THE System SHALL treat the deliverable as incomplete.
6. THE System SHALL define Evidence_Record as a structured record containing exactly four required fields (`test_file`, `test_name`, `output_hash`, `collected_at`); a status transition to `proven` SHALL be rejected if any of the four fields is absent or empty. *(Z3 CHECK-7a/7c verified: PASSED with missing `output_hash` or zero fields is UNSAT.)*
7. WHEN a requirement is amended after plan approval, THE System SHALL reset its coverage item to `unproven` and SHALL require re-proving with fresh evidence before the item may count toward COMPLETE; an amended-but-not-reproven item SHALL be treated as `unproven`. *(REQ-COV-007; Z3 CHECK-10a/10b verified: amended ∧ ¬reproven ∧ complete is UNSAT.)*

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

**Baseline block:** B08 | **PRD references:** REQ-VERIFY-001..008, REQ-SPEC-018

#### Acceptance Criteria

1. THE System SHALL verify each Slice across four core layers — structural (lint, type checking, AST analysis), semantic (unit and integration tests), behavioral (E2E via Playwright), and security (SAST via Semgrep_CodeQL) — plus a fifth NFR layer (performance and accessibility) for items that carry those obligations (see criteria 7–8).
2. THE System SHALL perform completion verification with the independent Verifier that has no write access to the implementation; the implementer SHALL NOT verify its own output.
3. WHEN a behavioral check runs, THE Verifier SHALL produce a captured artifact (trace, screenshot, or test output) attached as an Evidence_Record.
4. WHEN a file edit completes, THE PostToolUse_Hook SHALL run lint, SAST, and wiring checks and, on failure, SHALL return the specific errors to the agent for correction on its next turn. (THE PostToolUse_Hook SHALL NOT be relied upon to undo the edit; see the PreToolUse_Hook for prevention.)
5. IF a subagent's result lacks required evidence markers, THEN THE SubagentStop_Hook SHALL block acceptance of that result.
6. THE System SHALL set the target line-coverage threshold on touched files to a numeric DEFAULT of 85% (configurable), failing the Slice if coverage falls below the threshold.
7. WHERE a coverage item is a `performance` NFR, THE Verifier SHALL measure it with a load/perf tool (e.g., k6 or Lighthouse) against its quantified threshold (e.g., p95 latency, Core Web Vitals) and SHALL mark the item `failed` if the threshold is not met. *(REQ-VERIFY-007.)*
8. WHERE a coverage item is an `accessibility` NFR or a UI screen, THE Verifier SHALL run an accessibility checker (e.g., axe-core) requiring zero WCAG-A/AA violations on covered screens and SHALL verify UI-screen completeness (empty, loading, and error states present). *(REQ-VERIFY-008.)*
9. WHEN a subagent returns a result, THE SubagentStop_Hook SHALL reject it if the `omission_declaration` field is null or absent; every subagent SHALL explicitly declare what it did NOT implement or cover, so silent omissions are surfaced rather than hidden. *(REQ-SPEC-018; Z3 CHECK-13a/13b verified: null omission_declaration ∧ result accepted is UNSAT.)*

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

**Baseline block:** B10 | **PRD references:** REQ-STATE-001..005

#### Acceptance Criteria

1. THE System SHALL persist all mutable run state outside model context, in files, git history, and the durable Postgres store.
2. WHEN context compaction is imminent, THE PreCompact_Hook SHALL checkpoint progress and evidence records before context is trimmed.
3. WHEN a session starts, THE SessionStart_Hook SHALL load git status, the progress file, and the Coverage_Model so a resumed session re-orients deterministically.
4. THE System SHALL record an incremental commit per completed Slice as the durable execution trail and rollback point.
5. WHEN a session resumes, THE System SHALL recompute the durable-state hash and compare it to the stored `state_hash`; IF they differ, THEN THE PreToolUse_Hook SHALL block the first write of the resumed session (fail closed) until an operator reconciles the state. SessionStart computes the hash but cannot block; enforcement is at PreToolUse. *(REQ-STATE-005; Z3 CHECK-11a/11b verified: resumeHashMismatch ∧ runProceeds is UNSAT.)*

---

### Requirement 12: Observability

**User Story:** As an operator, I want a live, requirement-tagged trace of what the agent is doing and every gate decision, so I can observe and audit mid-flight.

**Baseline block:** B11 | **PRD references:** REQ-OBS-001..005

#### Acceptance Criteria

1. THE System SHALL emit OTel spans for every model call, tool invocation, and subagent task. *(Note: OTel GenAI semantic conventions are experimental as of mid-2026 — pin versions and opt in via `OTEL_SEMCONV_STABILITY_OPT_IN=gen_ai_latest_experimental`; treat them as unstable.)*
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

**Baseline block:** B13 | **PRD references:** REQ-LOOP-001..005

#### Acceptance Criteria

1. WHILE a control loop runs, THE System SHALL enforce a hard iteration cap (DEFAULT = 25 turns per Slice) and a token/cost budget per Slice.
2. IF the iteration cap OR the cost budget OR the no-progress condition is reached, THEN THE System SHALL terminate the run to HANDOFF — a terminal state distinct from COMPLETE — and SHALL NOT mark the deliverable complete. *(Z3 CHECK-3 verified.)* No-progress is operationalized as: zero coverage items flipped from `unproven` to `proven` AND zero commits produced, both conditions true simultaneously across the last N consecutive Slices (DEFAULT N = 3). *(Z3 CHECK-8a/8b verified.)*
3. IF a Slice exhausts its retry budget (DEFAULT = 3 retries), THEN THE System SHALL fail gracefully and hand off to a human rather than retrying indefinitely.
4. THE System SHALL trace-log agent reasoning and tool calls and retain human-readable evidence so a human can audit why the agent acted, bounding comprehension debt.
5. WHEN the iteration cap, the cost/token budget, OR the no-progress predicate routes a run to HANDOFF, THE Stop_Hook SHALL ALLOW termination (exit 0) and SHALL NOT block (exit 2); blocking a HANDOFF would force the agent to continue (the infinite-block defect). Only the unproven-items completion gate — with no cap/budget/no-progress trigger active — blocks with exit 2. *(REQ-LOOP-005; Z3 CHECK-5b/5c/8c verified: blocking on a HANDOFF trigger is UNSAT.)*

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
4. WHILE the agent executes untrusted code, THE System SHALL run it in an isolated sandbox.
5. THE System SHALL never place credentials or secrets in prompts, spans, or URLs, and SHALL treat retrieved or model-predicted content as untrusted input data, not as instructions.

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

1. THE System SHALL enforce the following DEFAULT numeric thresholds: line coverage on touched files ≥ 85% (configurable); 0 HIGH or CRITICAL SAST findings; ≤15 minutes per Slice; iteration cap of 25 turns per Slice; retry budget of 3 per Slice; spec-completion loop cap of 7 passes; no-progress window N = 3 consecutive Slices; hook validator timeout of 60 seconds; telemetry export interval ≤ 5 seconds; cost/token budget per Slice (DEFAULT 1,000,000 tokens, operator-configurable); reasoning-loop bound K (DEFAULT 3).
2. THE System SHALL treat all numeric thresholds as configurable DEFAULTs, with changes requiring explicit operator override.

---

## Additional Governance Requirements

### Requirement 21: Audit-Log Tamper Detection

**User Story:** As an auditor, I want every gate decision recorded in a hash-chained, tamper-evident log, so I can prove after the fact that no allow/block decision was altered or deleted.

**Baseline block:** B16 | **PRD references:** REQ-AUDIT-001..003

#### Acceptance Criteria

1. WHEN any hook makes a gate decision, THE System SHALL append a record (event, tool, decision, reason, requirement ID, acting agent, timestamp) to the hash-chained `gate_audit_log`, where each entry's `entry_hash = sha256(canonical_row_json || prev_hash)` and the first entry's `prev_hash` is a fixed genesis sentinel. *(REQ-AUDIT-001.)*
2. THE System SHALL verify the audit-log hash chain at SessionStart (informational) and as a required CI status check at merge (blocking on any broken link). *(REQ-AUDIT-002.)*
3. IF any audit-log entry's recomputed `entry_hash` does not match its stored value, THEN THE System SHALL flag the chain as broken and fail the merge gate. *(REQ-AUDIT-003; Property 28.)*

---

### Requirement 22: Research-Claim Authority Labeling

**User Story:** As a product owner, I want every external claim the Research_Sub_Agent makes to carry a source and an authority tier, so domain-baseline checklists are built on verifiable evidence rather than unsourced model assertions.

**Baseline block:** B19 | **PRD references:** REQ-SPEC-017

#### Acceptance Criteria

1. WHEN the Research_Sub_Agent drafts a Domain_Baseline_Checklist, THE System SHALL require every external claim to carry a non-empty `source_url` and an `authority_tier` from {primary, standard, peer-reviewed, blog, vendor, social}. *(REQ-SPEC-017.)*
2. IF a claim is supported only by `blog`, `vendor`, or `social` sources, THEN THE System SHALL flag it for human review before the claim may inform the checklist. *(REQ-SPEC-017; Property 29.)*

---

## Critical Invariants (Z3-Verified)

The following invariants are machine-checked by `verification/formal_verification_merged.py` (Z3 v4.16.0, 34/34 assertions passing). They are non-negotiable constraints on any implementation:

1. **Completion from facts only:** Completion is decided only by deterministic gates from verifiable facts. No prediction or self-assessment can gate. *(CHECK-5: UNSAT)*
2. **Mutually exclusive terminal states:** COMPLETE and HANDOFF are mutually exclusive terminal states. Cap/budget/no-progress terminate only to HANDOFF. *(CHECK-3: UNSAT for naive-cap → COMPLETE under unproven)*
3. **No code-write without approved plan:** No implementation Write or Edit tool may run unless `plan-approved.json` exists. *(CHECK-4f: UNSAT)*
4. **No new slice while prior slice is unproven:** A new worktree or slice cannot start while any prior-slice item is `unproven`. *(CHECK-6a: UNSAT)*
5. **Evidence schema enforced:** An item transition to `proven` with missing `output_hash` or with zero evidence fields is UNSAT. *(CHECK-7a/7c: UNSAT)*
6. **UNMAPPED blocks advancement:** Advancement to implementation while any domain-baseline item is UNMAPPED is UNSAT. *(CHECK-9a: UNSAT)*
7. **No-progress → HANDOFF only:** No-progress condition (zero items proven AND zero commits across N=3 slices) routes only to HANDOFF, never COMPLETE. *(CHECK-8b: UNSAT)*
8. **Amendment monotonicity:** An amended-but-not-reproven requirement cannot reach COMPLETE. *(CHECK-10a: UNSAT)*
9. **Resumed-state integrity:** A resumed run whose state hash mismatches the durable store cannot proceed. *(CHECK-11a: UNSAT)*
10. **Checklist-approval before use:** A DRAFT (unapproved) checklist cannot be used for proactive discovery. *(CHECK-12a: UNSAT)*
11. **Omission declaration:** A subagent result with a null or absent `omission_declaration` cannot be accepted. *(CHECK-13a: UNSAT)*
12. **HANDOFF exits 0:** Cap, budget, and no-progress route to HANDOFF and ALLOW termination (exit 0); blocking on any HANDOFF trigger is impossible. *(CHECK-5b/5c/8c: UNSAT)*

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
