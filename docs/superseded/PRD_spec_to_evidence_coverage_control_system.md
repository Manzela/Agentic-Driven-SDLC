# Product Requirements Document — Spec-to-Evidence Coverage Control System (Claude Code Substrate)

> ⚠️ **SUPERSEDED / HISTORICAL.** This PRD is a non-authoritative input retained for provenance. The canonical specification is `.kiro/specs/spec-to-evidence-control/` and the authoritative harness is `verification/formal_verification_merged.py`. **Counts in this document are stale** — the "21/21" figures below reflect the deprecated `formal_verification.py`; the current harness self-counts **34 assertions** (`Result: 34/34 checks passed`, exit 0). Do not cite this document's counts.

**Artifact type:** Canonical, formally-verified PRD — capstone hand-off for an Agentic AI Coding Agent
**Authoring discipline:** Principal PM (systems engineering) × Formal Verification Engineer
**Formal-validation status:** Machine-checked with Microsoft Research **Z3 v4.16.0** — **21/21 assertions returned their expected verdict** (harness: `formal_verification.py`, re-runnable; exit 0 = all pass). Original 12 checks reproduced; 9 extended checks added covering gap-closure requirements REQ-EXEC-005, REQ-COV-006, REQ-LOOP-002 refinement, and REQ-SPEC-011 independence.
**Date:** June 15, 2026

> **Scope note (stated, not assumed silently).** This PRD specifies the *Spec-to-Evidence Coverage Control System* — the autonomous agentic software-delivery control plane defined across the preceding architecture work — **not** a generic SaaS app. Its purpose: *minimize human micro-steering by converting product intent into a traceable, machine-verifiable coverage model that governs agent execution and rejects incomplete delivery.* The SaaS auth example in the source meta-prompt is used only to illustrate the proactive-discovery method; the domain baseline below is the one appropriate to *this* system. If a different target was intended, this is the one assumption to redirect.

> **The one governing invariant (repeated because it is load-bearing).** **Deterministic gates — Claude Code hooks, CI, OPA — decide whether delivery is complete, computed solely from verifiable facts. Model self-assessment and probabilistic predictions only inform; they never gate.** Every requirement below is consistent with this invariant, and Z3 CHECK-5 proves a prediction cannot move a gate decision.

---

## STEP 1 — Domain-Baseline Coverage Checklist (Prevention of Omissions)

**Method.** You cannot prove the absence of something absent; a curated baseline of the system's essential capability blocks guarantees no core block is silently omitted. Every baseline item **must** map to ≥1 User Story and ≥1 EARS requirement. **Enforcement:** any baseline item with zero mapped requirements is flagged `UNMAPPED` and blocks PRD sign-off. The matrix below has **zero `UNMAPPED` items**.

| # | Domain-baseline capability block | User Story | EARS Requirement IDs | Status |
|---|----------------------------------|-----------|----------------------|--------|
| B01 | Spec compilation (intent → atomic, testable EARS requirements) | US-01 | REQ-SPEC-001..004 | MAPPED |
| B02 | Proactive discovery (infer implied/competitive features) | US-02 | REQ-SPEC-010..012 | MAPPED |
| B03 | Spec-completion loop (contradiction/gap closure to provable completeness) | US-03 | REQ-SPEC-020..024 | MAPPED |
| B04 | Coverage model (default-unproven `feature_list.json`) | US-04 | REQ-COV-001..005 | MAPPED |
| B05 | Traceability (bidirectional req↔code↔test↔evidence↔commit↔owner) | US-05 | REQ-TRACE-001..004 | MAPPED |
| B06 | Incremental execution control (bounded slices, worktrees) | US-06 | REQ-EXEC-001..004 | MAPPED |
| B07 | Wiring verification (detect "exists in code but never connected") | US-07 | REQ-EXEC-010..012 | MAPPED |
| B08 | Verification engine (structural + semantic + behavioral; independent evaluator) | US-08 | REQ-VERIFY-001..006 | MAPPED |
| B09 | Completion gate (fail-closed; zero unproven) | US-09 | REQ-GATE-001..005 | MAPPED |
| B10 | Session continuity & durable state (file + git + Postgres) | US-10 | REQ-STATE-001..004 | MAPPED |
| B11 | Awareness / observability (OTel spans, requirement-ID tagging, live trace) | US-11 | REQ-OBS-001..005 | MAPPED |
| B12 | Mid-flight steering (deterministic hooks) | US-12 | REQ-STEER-001..006 | MAPPED |
| B13 | Anti-loopmaxxing controls (iteration cap, token/cost budget, no-progress, handoff) | US-13 | REQ-LOOP-001..004 | MAPPED |
| B14 | Orchestration (Claude Code subagents/hooks inner; durable outer loop optional) | US-14 | REQ-ORCH-001..003 | MAPPED |
| B15 | Durable storage (managed Postgres + evidence store) | US-15 | REQ-STORE-001..003 | MAPPED |
| B16 | Supply-chain & security gates (SAST, secrets, signed provenance) | US-16 | REQ-SEC-001..005 | MAPPED |
| B17 | Human-in-the-loop approval (plan mode, approval marker, PR review) | US-17 | REQ-HITL-001..003 | MAPPED |
| B18 | Predictive routing (OPTIONAL acceleration aid; read-only, off the gate) | US-18 | REQ-PRED-001..003 | MAPPED |
| B19 | Domain-baseline checklist sourcing (how checklists are produced, confirmed, and maintained per product class) | US-02 | REQ-SPEC-013..015 | MAPPED |

---

## STEP 2 — User Stories & EARS Requirements

**EARS pattern legend.** Ubiquitous: *The system SHALL …*. Event-driven: *WHEN <trigger> THEN the system SHALL …*. State-driven: *WHILE <state> the system SHALL …*. Unwanted behaviour: *IF <condition> THEN the system SHALL …*. Optional: *WHERE <feature included> the system SHALL …*. Each requirement carries an enforcement label: **[DET]** deterministic (hook/CI/OPA/exit-code) or **[PROB]** probabilistic (model output, advisory only).

### B01 Spec compilation — US-01
*As a product owner, I want terse intent compiled into atomic, individually-testable requirements with IDs and acceptance criteria, so the agent and I share one machine-checkable definition of scope.*
- **REQ-SPEC-001 [DET]** (Ubiquitous): The system SHALL compile product intent into atomic requirements, each with a unique ID, an EARS statement, a priority, and ≥1 machine-checkable acceptance criterion.
- **REQ-SPEC-002 [DET]** (Unwanted): IF a candidate requirement contains a non-deterministic adjective (e.g., "fast", "secure", "scalable", "optimized") without a numeric bound, THEN the system SHALL reject it and require a quantified criterion before acceptance.
- **REQ-SPEC-003 [DET]** (Ubiquitous): The system SHALL persist compiled requirements as version-controlled artifacts in the repository (not in model context alone).
- **REQ-SPEC-004 [DET]** (Event-driven): WHEN a requirement is authored or modified THEN the system SHALL validate it against the EARS schema and assign exactly one of the five EARS patterns.

### B02 Proactive discovery — US-02
*As a founder with limited context, I want the system to infer the implied, industry-standard features I did not enumerate, so a complete competitive product is specified without me hand-listing every micro-feature.*
- **REQ-SPEC-010 [PROB]** (Ubiquitous): The system SHALL expand intent against a curated domain-baseline checklist for the detected product class and propose implied requirements for each baseline item.
- **REQ-SPEC-011 [DET]** (Unwanted): IF any domain-baseline item has zero proposed requirements after discovery, THEN the system SHALL flag it `UNMAPPED` and SHALL NOT advance to implementation.
- **REQ-SPEC-012 [DET]** (State-driven): WHILE proactive discovery is active, the system SHALL present every inferred requirement for human confirmation and SHALL mark inferred-vs-stated provenance on each.
- **REQ-SPEC-013 [DET]** (Event-driven): WHEN a new product class is encountered for the first time THEN the system SHALL run a research sub-agent that queries competitive analysis, industry standards, and open-source reference implementations to draft a domain-baseline checklist for that product class, and SHALL present the draft for human review before use.
- **REQ-SPEC-014 [DET]** (Ubiquitous): The system SHALL persist domain-baseline checklists as version-controlled artifacts in the repository, named by product class, so they accumulate across projects and do not need to be re-derived from scratch.
- **REQ-SPEC-015 [DET]** (Event-driven): WHEN a domain-baseline checklist is used THEN the system SHALL record which checklist version was used and link it to the `feature_list.json` so the derivation is auditable.

### B03 Spec-completion loop — US-03
*As an operator, I want spec elaboration to run until the spec is provably free of contradictions, ambiguities, and gaps — bounded so it cannot loop forever or "declare done" to escape, so I get a complete spec without endless token burn.*
- **REQ-SPEC-020 [DET]** (Ubiquitous): The system SHALL judge spec completeness with a non-LLM validator returning `{contradictions, ambiguities, uncovered, violation_count}`; the authoring agent SHALL have no vote in the verdict.
- **REQ-SPEC-021 [DET]** (Event-driven): WHEN the spec agent attempts to end its turn AND `violation_count > 0` THEN a `Stop` hook SHALL block termination and return the enumerated violations.
- **REQ-SPEC-022 [DET]** (Unwanted): IF a spec-completion pass does not strictly reduce `violation_count` versus the prior pass, THEN the system SHALL halt and hand off to a human (no infinite retry).
- **REQ-SPEC-023 [DET]** (Unwanted): IF the spec-completion loop reaches its hard pass cap (DEFAULT = 7), THEN the system SHALL halt to human handoff and surface remaining violations.
- **REQ-SPEC-024 [DET]** (Event-driven): WHEN `violation_count == 0` THEN the system SHALL emit the validated spec + `features.json` and request human plan approval before any implementation.

### B04 Coverage model — US-04
*As a delivery lead, I want one machine-readable map of every required feature/behavior/NFR, defaulting to "unproven," so completeness is a queryable fact rather than a claim.*
- **REQ-COV-001 [DET]** (Ubiquitous): The system SHALL maintain `feature_list.json` in which every item has an ID, a type ∈ {functional, NFR, WIRING}, dependencies, acceptance criteria, and a status defaulting to `unproven`.
- **REQ-COV-002 [DET]** (Unwanted): IF a tool action would delete, reorder, or modify an existing coverage item's identity, THEN a `PreToolUse` hook SHALL block it; status MAY change only `unproven → proven`.
- **REQ-COV-003 [DET]** (Event-driven): WHEN an item is set `proven` THEN the system SHALL require attached evidence (test file, test name, output hash, collection timestamp); absent evidence, the transition SHALL be rejected.
- **REQ-COV-004 [DET]** (Ubiquitous): The system SHALL represent architectural WIRING and NFR items as first-class coverage items, not as comments or afterthoughts.
- **REQ-COV-005 [DET]** (State-driven): WHILE any in-scope item is `unproven`, the system SHALL treat the deliverable as incomplete.
- **REQ-COV-006 [DET]** (Ubiquitous): The system SHALL define evidence as a structured record containing exactly four required fields: `test_file` (path to the test), `test_name` (unique test identifier), `output_hash` (content-addressed hash of the test output), and `collected_at` (ISO-8601 timestamp). An item transition to `proven` SHALL be rejected if any of the four fields is absent. *(Z3 CHECK-7a/7c verified: PASSED with missing hash or zero fields is UNSAT.)*

### B05 Traceability — US-05
*As an auditor, I want every requirement linked forward to verification and every code unit linked back to a requirement, so coverage is provable end-to-end.*
- **REQ-TRACE-001 [DET]** (Ubiquitous): The system SHALL maintain bidirectional links requirement↔implementation↔test↔evidence↔commit↔owner in the durable store.
- **REQ-TRACE-002 [DET]** (Event-driven): WHEN a commit is created THEN the system SHALL require ≥1 referenced requirement ID in the commit trailer.
- **REQ-TRACE-003 [DET]** (Unwanted): IF an implementation unit references no requirement, or a requirement maps to no verification, THEN the orphan-detection check SHALL fail the run.
- **REQ-TRACE-004 [DET]** (Ubiquitous): The system SHALL stamp the active `requirement.id` onto every telemetry span via W3C Baggage so traceability is reconstructable from the live trace.

### B06 Incremental execution control — US-06
*As an engineer, I want the agent forced to implement one bounded slice at a time in isolation, so it cannot one-shot a sprawling, partial change.*
- **REQ-EXEC-001 [DET]** (Ubiquitous): The system SHALL restrict each coding sub-agent session to exactly one highest-priority `unproven` item.
- **REQ-EXEC-002 [DET]** (State-driven): WHILE a slice is in progress, the system SHALL isolate it in a dedicated git worktree to prevent cross-slice collisions.
- **REQ-EXEC-003 [PROB]** (Ubiquitous): The system SHALL target a per-slice size of ≤15 minutes / ≤1 feature and SHALL produce one atomic commit per completed slice.
- **REQ-EXEC-004 [DET]** (Unwanted): IF no implementation tool may run because no plan is approved (REQ-HITL-001), THEN the system SHALL block the slice from starting.
- **REQ-EXEC-005 [DET]** (Unwanted): IF any prior-slice coverage item is `unproven`, THEN a `PreToolUse` hook SHALL block initiation of a new worktree or new slice assignment, preventing forward progress until the prior item is verified. *(Z3 CHECK-6a verified: newSliceStarting ∧ priorItemUnproven is UNSAT.)*

### B07 Wiring verification — US-07
*As a reviewer, I want components that compile but are never connected to be detected, so "looks done" cannot pass as "is wired."*
- **REQ-EXEC-010 [DET]** (Ubiquitous): The system SHALL run static call-graph / dead-code analysis on changed files and SHALL represent each wiring obligation as a WIRING coverage item.
- **REQ-EXEC-011 [DET]** (Unwanted): IF a handler, route, job, or callback exists but is unreachable from any real execution path, THEN the verification stage SHALL mark the corresponding WIRING item `failed`.
- **REQ-EXEC-012 [DET]** (Event-driven): WHEN a WIRING item is claimed `proven` THEN an integration test exercising the real execution path SHALL be required as evidence.

### B08 Verification engine — US-08
*As a quality owner, I want behavior, semantics, and security verified by an evaluator that did not write the code, so the system never grades its own homework.*
- **REQ-VERIFY-001 [DET]** (Ubiquitous): The system SHALL verify each slice across structural (lint/type/AST), semantic (tests), behavioral (E2E), and security (SAST) layers.
- **REQ-VERIFY-002 [DET]** (Ubiquitous): The system SHALL perform completion verification with an independent evaluator agent that has no write access to the implementation; the implementer SHALL NOT verify its own output.
- **REQ-VERIFY-003 [DET]** (Event-driven): WHEN a behavioral check runs THEN it SHALL produce a captured artifact (trace/screenshot/test output) attached as evidence.
- **REQ-VERIFY-004 [DET]** (Event-driven): WHEN a file edit completes THEN a `PostToolUse` hook SHALL run lint + SAST + wiring checks and, on failure, SHALL return the specific errors to the agent for correction on its next turn. (The hook SHALL NOT be relied upon to undo the edit — see REQ-STEER-002.)
- **REQ-VERIFY-005 [DET]** (Unwanted): IF a sub-agent's result lacks required evidence markers, THEN a `SubagentStop` hook SHALL block acceptance of that result.
- **REQ-VERIFY-006 [DET]** (Ubiquitous): The system SHALL set the target line-coverage threshold on touched files to a numeric DEFAULT = 85% (configurable), failing the slice below it.

### B09 Completion gate — US-09
*As a delivery owner, I want "done" to be impossible while any requirement is unproven, enforced where the model cannot talk past it.*
- **REQ-GATE-001 [DET]** (Ubiquitous): The system SHALL compute the completion verdict solely from verifiable facts (zero `unproven` in-scope items, passing tests, present evidence) evaluated against the actual repository state.
- **REQ-GATE-002 [DET]** (Unwanted): IF the agent attempts to terminate as COMPLETE WHILE any in-scope requirement is `unproven`, THEN a `Stop` hook SHALL block termination. *(Z3 CHECK-1, CHECK-3 verified.)*
- **REQ-GATE-003 [DET]** (Event-driven): WHEN a merge is attempted THEN a required CI status check SHALL run an OPA/Conftest policy that fails the merge if any approved requirement has zero passing evidence (the zero-evidence query MUST return 0 rows).
- **REQ-GATE-004 [DET]** (State-driven): WHILE a `Stop`-hook block is active, the system SHALL set `stop_hook_active` to prevent the hook re-triggering itself, and SHALL release only when the blocking condition clears.
- **REQ-GATE-005 [DET]** (Ubiquitous): The completion gate SHALL be fail-closed and non-bypassable by configuration; ambiguous states resolve to "blocked," not "passed."

### B10 Session continuity & durable state — US-10
*As an operator of long runs, I want state to survive context limits and crashes, so work resumes exactly where it stopped.*
- **REQ-STATE-001 [DET]** (Ubiquitous): The system SHALL persist all mutable run state outside model context (in files, git history, and the durable store).
- **REQ-STATE-002 [DET]** (Event-driven): WHEN context compaction is imminent THEN a `PreCompact` hook SHALL checkpoint progress and evidence before context is trimmed.
- **REQ-STATE-003 [DET]** (Event-driven): WHEN a session starts THEN a `SessionStart` hook SHALL load git status, progress file, and the coverage model so a resumed session re-orients deterministically.
- **REQ-STATE-004 [DET]** (Ubiquitous): The system SHALL record an incremental commit per completed slice as the durable execution trail and rollback point.

### B11 Awareness / observability — US-11
*As an operator, I want a live, requirement-tagged trace of what the agent is doing and every gate decision, so I can observe and audit mid-flight.*
- **REQ-OBS-001 [DET]** (Ubiquitous): The system SHALL emit OpenTelemetry spans for every model call, tool invocation, and sub-agent task. *(Note: OTel GenAI semantic conventions are **experimental / "Status: Development"** as of mid-2026 — pin versions and opt in via `OTEL_SEMCONV_STABILITY_OPT_IN=gen_ai_latest_experimental`; do not treat the conventions as stable.)*
- **REQ-OBS-002 [DET]** (State-driven): WHILE a run is in progress, the system SHALL stream each span to the backend as it closes (export interval DEFAULT ≤ 5s), not batched at run-end.
- **REQ-OBS-003 [DET]** (Event-driven): WHEN a hook makes a gate decision THEN the system SHALL emit that decision (event, tool, allow/block, reason, requirement ID) to the same trace endpoint as agent spans.
- **REQ-OBS-004 [DET]** (Ubiquitous): The system SHALL propagate the active `requirement.id` to all child spans via a W3C Baggage span processor.
- **REQ-OBS-005 [DET]** (Optional): WHERE a managed observability backend is used, the system SHALL document its license (Langfuse MIT core; SigNoz MIT Expat core; **Arize Phoenix Elastic License 2.0 — source-available, not OSI, no hosted-service offering**) so backend choice is compliance-aware.

### B12 Mid-flight steering (deterministic hooks) — US-12
*As a platform owner, I want the only thing that can halt or redirect a running agent to be deterministic hooks, so enforcement does not depend on the model's intentions.*
- **REQ-STEER-001 [DET]** (Ubiquitous): The system SHALL treat Claude Code hooks (not prompts or CLAUDE.md) as the sole deterministic mid-flight intervention layer.
- **REQ-STEER-002 [DET]** (Ubiquitous): The system SHALL use `PreToolUse` as the only true prevention gate (exit 2 / deny blocks before execution); `PostToolUse` SHALL be treated as a next-turn forcing function that **cannot undo** an already-executed action.
- **REQ-STEER-003 [DET]** (Unwanted): IF a tool call targets a protected artifact (tests, coverage-model schema, CI config) or a destructive operation, THEN a `PreToolUse` command-type hook SHALL block it.
- **REQ-STEER-004 [DET]** (Ubiquitous): For hard policy, the system SHALL use command-type hooks (which fail closed), not HTTP/MCP hooks (which fail open).
- **REQ-STEER-005 [DET]** (Ubiquitous): The system SHALL honor the hook exit-code contract: 0 = proceed, 2 = blocking error fed to the model via stderr, any other non-zero = non-blocking (exit 1 does NOT block).
- **REQ-STEER-006 [DET]** (Ubiquitous): No gate decision SHALL read a probabilistic prediction; gate outcomes depend only on facts. *(Z3 CHECK-5 verified: a differing prediction cannot produce a differing gate decision.)*

### B13 Anti-loopmaxxing controls — US-13
*As a budget owner, I want runaway loops impossible — hard caps, budgets, stuck-detection, and human handoff — so a hallucinating agent cannot burn the budget or accrue comprehension debt.*
- **REQ-LOOP-001 [DET]** (State-driven): WHILE a control loop runs, the system SHALL enforce a hard iteration cap (e.g., `--max-turns`, DEFAULT = 25/slice) and a token/cost budget.
- **REQ-LOOP-002 [DET]** (Unwanted): IF the iteration cap OR the cost budget OR a no-progress condition is reached, THEN the system SHALL terminate the run to HUMAN HANDOFF — a terminal state distinct from COMPLETE — and SHALL NOT mark the deliverable complete. *(Z3 CHECK-3 verified: cap-reached ⇒ HANDOFF resolves the conflict with the completion gate.)* **No-progress is operationalized as: zero coverage items flipped from `unproven` to `proven` AND zero commits produced across the last N consecutive slices (DEFAULT N = 3). Both signals must be true simultaneously to fire.** *(Z3 CHECK-8a/8b verified: the operationalized predicate is reachable and correctly routes to HANDOFF.)*
- **REQ-LOOP-003 [DET]** (Unwanted): IF a slice exhausts its retry budget (DEFAULT = 3), THEN the system SHALL fail gracefully and hand off to a human rather than retry indefinitely.
- **REQ-LOOP-004 [DET]** (Ubiquitous): The system SHALL trace-log agent reasoning and tool calls and retain human-readable evidence so a human can audit *why* the agent acted, bounding comprehension debt.

### B14 Orchestration — US-14
*As an architect, I want the inner loop run by Claude Code's own primitives and durability added only when truly needed, so we avoid redundant orchestration.*
- **REQ-ORCH-001 [DET]** (Ubiquitous): The system SHALL use Claude Code subagents + hooks as the inner planner/implementer/verifier orchestrator and SHALL NOT introduce an external agent-reasoning framework for the inner loop by default.
- **REQ-ORCH-002 [DET]** (Optional): WHERE crash-safe multi-hour/multi-day runs are required, the system SHALL wrap the loop in a durable-execution engine (Temporal or Inngest) invoking `claude -p` as a durable step, with each tool call as a separate activity.
- **REQ-ORCH-003 [DET]** (Ubiquitous): The system SHALL keep peer-to-peer Agent Teams (experimental) off the delivery-gating path until the feature exits experimental status and supports session resumption.

### B15 Durable storage — US-15
*As a data owner, I want traceability, run state, and evidence in one managed store, so the system's memory is durable and queryable.*
- **REQ-STORE-001 [DET]** (Ubiquitous): The system SHALL persist requirements, coverage state, traceability links, evidence, and run state in a managed Postgres database.
- **REQ-STORE-002 [DET]** (Event-driven): WHEN evidence is captured THEN the system SHALL store the artifact (or a content-addressed reference) and link it to the requirement and commit.
- **REQ-STORE-003 [DET]** (Ubiquitous): The system SHALL keep the durable store as the single source of truth for coverage queries, reconstructable independently of any model session.

### B16 Supply-chain & security gates — US-16
*As a security owner, I want agent-generated code held to SAST, secrets, and provenance gates, so autonomy does not introduce supply-chain risk.*
- **REQ-SEC-001 [DET]** (Event-driven): WHEN code is changed THEN SAST (Semgrep + CodeQL) SHALL run in CI and SHALL fail the run on any HIGH/CRITICAL finding.
- **REQ-SEC-002 [DET]** (Unwanted): IF a secret, credential, or token is detected in a diff, THEN the system SHALL block the commit/merge.
- **REQ-SEC-003 [DET]** (Event-driven): WHEN an artifact is built on merge THEN the system SHALL generate signed SLSA build provenance (e.g., `actions/attest-build-provenance`) verifiable via `gh attestation verify`.
- **REQ-SEC-004 [DET]** (State-driven): WHILE the agent executes untrusted code, the system SHALL run it in an isolated sandbox.
- **REQ-SEC-005 [DET]** (Ubiquitous): The system SHALL never place credentials/secrets in prompts, spans, or URLs, and SHALL treat retrieved/predicted content as untrusted input (data, not instructions).

### B17 Human-in-the-loop approval — US-17
*As the accountable human, I want to approve the complete plan before code starts and review before merge, with that approval enforced deterministically.*
- **REQ-HITL-001 [DET]** (Unwanted): IF no approval marker (e.g., `plan-approved.json`) exists, THEN a `PreToolUse` hook SHALL block all implementation `Write`/`Edit` tools.
- **REQ-HITL-002 [DET]** (Event-driven): WHEN the validated spec + `features.json` are ready THEN the system SHALL present them in plan mode for human approval and missing-context injection before unlocking implementation.
- **REQ-HITL-003 [DET]** (Ubiquitous): The system SHALL require human PR review (a required reviewer in a repository ruleset) before merge to the protected branch.

### B18 Predictive routing — US-18 (OPTIONAL)
*As a developer, I want optional predictive "next-step" routing to speed the agent toward the right context, without it ever overriding a gate, so I get acceleration without sacrificing the enforcement guarantee.*
- **REQ-PRED-001 [PROB]** (Optional): WHERE predictive next-step routing is enabled, the system SHALL inject predictions only as advisory context (e.g., via a `UserPromptSubmit`/`SessionStart` context-injection hook or an MCP retrieve tool).
- **REQ-PRED-002 [DET]** (Unwanted): IF a design routes a prediction into a block/allow gate decision, THEN it SHALL be rejected; predictions SHALL NOT emit, and gates SHALL NOT read, gate decisions. *(Z3 CHECK-5 verified.)*
- **REQ-PRED-003 [DET]** (Optional): WHERE predictive routing is enabled, the system SHALL tag predicted-routing spans distinctly and measure prediction acceptance/accuracy so routing can be disabled on drift. *(Implementation note: build on battle-tested primitives — Speculative Actions, semantic-router / vLLM Semantic Router, the Claude memory tool + context editing — not on the pre-product "PredictStream," which has no shipping release as of mid-2026.)*

---

## STEP 3 — Formal Logic Validation via Z3 SMT-Solver

**Discipline:** Z3 must *prove*, not opine. The formulas below were executed against **real Z3 v4.16.0** (harness `formal_verification.py`); the verdicts are **machine-checked**, and the harness exits 0 only if all match. This is a bounded model of the control plane's critical invariants, not of every micro-requirement; the SMT-LIB should be re-run as a CI gate and extended as `feature_list.json` expands.

### 3.1 Model variables (Booleans)
`maint, writeReq, writeAllowed, planApproved, codeWrite, unproven, complete, handoff, running, capReached, budgetExceeded, noProgress, evidence, testsPass, passed, gateBlock, adminSave, predA, predB, gateA, gateB`.

### 3.2 Core requirement encodings (SMT-LIB form)
```smt2
; REQ-GATE-001: the gate is a pure function of facts
(assert (= gateBlock unproven))
; REQ-GATE-002: cannot be COMPLETE while the gate blocks  ⇒ COMPLETE ⇒ ¬unproven
(assert (=> complete (not gateBlock)))
; REQ-HITL-001 / REQ-EXEC-004: no code-write without an approved plan
(assert (=> codeWrite planApproved))
; REQ-SEC / REQ-COV: reject writes while in maintenance mode
(assert (=> maint (not writeAllowed)))
; REQ-COV-001/003: PASSED requires evidence AND passing tests
(assert (=> passed (and evidence testsPass)))
; REQ-LOOP-002: cap/budget/no-progress ⇒ HANDOFF, never COMPLETE
(assert (=> (or capReached budgetExceeded noProgress) (and handoff (not complete))))
; terminal exclusivity
(assert (=> (or complete handoff) (not running)))
(assert (not (and complete handoff)))
```

### 3.3 Consistency, conflict-isolation, vacuity & independence — machine-checked verdicts

| Check | Assertion | Expected | **Z3 verdict** |
|-------|-----------|----------|----------------|
| **CHECK-1** | Core requirement set admits a clean successful-completion state | SAT | **sat ✓** |
| **CHECK-2a** | Conflict: `A: maint⇒¬write` vs `B(naive): adminSave⇒write` under `maint∧adminSave` | UNSAT | **unsat ✓** |
| **CHECK-2b** | Correction: `B′: (adminSave∧¬maint)⇒write` is satisfiable and still fires | SAT | **sat ✓** |
| **CHECK-3a** | Conflict: `C: unproven⇒¬complete` vs `D_bad: capReached⇒complete` under `cap∧unproven` | UNSAT | **unsat ✓** |
| **CHECK-3b** | Correction: `D_good: capReached⇒(handoff∧¬complete)` is satisfiable | SAT | **sat ✓** |
| **CHECK-4a** | Maintenance-reject guard reachable (`maint`, write rejected) — not dead | SAT | **sat ✓** |
| **CHECK-4b** | Writes remain possible outside maintenance — rule not vacuous | SAT | **sat ✓** |
| **CHECK-4c** | Stop-gate can fire (`unproven⇒block`) | SAT | **sat ✓** |
| **CHECK-4d** | Stop-gate can clear (`proven⇒allow`) | SAT | **sat ✓** |
| **CHECK-4e** | PASSED reachable with evidence+tests — coverage rule not vacuous | SAT | **sat ✓** |
| **CHECK-4f** | No model permits code-write without an approved plan — PreToolUse gate holds | UNSAT | **unsat ✓** |
| **CHECK-5** | A differing prediction cannot produce a differing gate decision | UNSAT | **unsat ✓** |
| **CHECK-6a** | New slice start blocked while prior item unproven [REQ-EXEC-005] | UNSAT | **unsat ✓** |
| **CHECK-6b** | New slice allowed when all prior items proven — scope gate not vacuous | SAT | **sat ✓** |
| **CHECK-7a** | PASSED without output hash is UNSAT — evidence schema enforced [REQ-COV-006] | UNSAT | **unsat ✓** |
| **CHECK-7b** | PASSED reachable with complete 4-field evidence — not vacuous | SAT | **sat ✓** |
| **CHECK-7c** | PASSED with zero evidence fields is UNSAT — fail-closed on empty evidence | UNSAT | **unsat ✓** |
| **CHECK-8a** | No-progress condition (zero proven items ∧ zero commits) is reachable | SAT | **sat ✓** |
| **CHECK-8b** | No-progress ∧ unproven ∧ complete is UNSAT — HANDOFF is only terminal [REQ-LOOP-002] | UNSAT | **unsat ✓** |
| **CHECK-8c** | Active progress suppresses no-progress condition — rule not vacuous | SAT | **sat ✓** |
| **CHECK-9a** | Advancement while UNMAPPED items exist is UNSAT [REQ-SPEC-011] | UNSAT | **unsat ✓** |
| **CHECK-9b** | Advancement allowed when all baseline items mapped — not vacuous | SAT | **sat ✓** |
| **CHECK-9c** | UNMAPPED gate and completion gate are independent — fully-proven mapped run reaches COMPLETE | SAT | **sat ✓** |

**Conflict isolation, explicitly named.**
- *Classic (illustrative):* **REQ pair (A, B-naive)** — "WHILE maintenance mode the system SHALL reject writes" vs. "WHEN an admin clicks save THEN the system SHALL write immediately" — is **UNSAT** under `maint ∧ adminSave`. **Resolution:** add the state-driven guard (`B′`: write only WHILE not in maintenance), restoring **SAT** while preserving liveness.
- *System-specific (material):* **REQ pair (REQ-GATE-002, naive cap-rule)** — "IF unproven THEN ¬COMPLETE" vs. a naive "WHEN cap reached THEN COMPLETE" — is **UNSAT** under `capReached ∧ unproven`. **Resolution (now encoded as REQ-LOOP-002):** cap/budget/no-progress terminate to **HANDOFF**, a terminal state *distinct from* COMPLETE. This is the formal justification for the distinct HANDOFF state.

**Vacuity result:** every critical guard (maintenance, gate-block, gate-clear, PASSED, plan-gate) is provably reachable; no requirement is dead or unfireable. **Independence result:** the completion gate is invariant to predictions — predictive routing cannot wave through incomplete delivery nor wrongly block correct delivery.

---

## STEP 4 — Deliverable Buckets & Production End-State

All deliverables are explicitly verifiable by an external validation script (`formal_verification.py` for the logic model; CI hooks/OPA for runtime).

### 4.1 User-Driven Deliverables (UI/UX behavioral states & interaction responses)
- **UD-1:** Plan-mode approval surface presenting the validated spec + `features.json`; implementation tools remain visibly locked until the approval marker exists (verify: `PreToolUse` blocks `Write` with no marker — REQ-HITL-001).
- **UD-2:** Live, requirement-filtered trace view: filtering by `requirement.id` shows the in-progress execution tree and every gate decision (verify: span filter returns agent + gate spans for the ID — REQ-OBS-003/004).
- **UD-3:** Human-handoff state: on cap/budget/no-progress, the operator receives the partial spec/result and the enumerated remaining violations, clearly labeled HANDOFF (not COMPLETE) (verify: REQ-LOOP-002; Z3 CHECK-3b).
- **UD-4:** PR review surface with required reviewer before merge (verify: ruleset blocks merge without approval — REQ-HITL-003).

### 4.2 Product-Driven Deliverables (business rules, thresholds, SLAs, retention)
- **PD-1:** Coverage-completeness rule = **0 `unproven` in-scope items** to permit completion (verify: zero-evidence OPA query returns 0 rows — REQ-GATE-003).
- **PD-2:** Quality thresholds = line coverage on touched files ≥ **85%** (DEFAULT, configurable); **0** HIGH/CRITICAL SAST findings (verify: REQ-VERIFY-006, REQ-SEC-001).
- **PD-3:** Execution bounds = **≤15 min / ≤1 feature** per slice; iteration cap **25 turns**; retry budget **3**; spec-loop cap **7 passes** (verify: REQ-EXEC-003, REQ-LOOP-001/003, REQ-SPEC-023).
- **PD-4:** Hook SLA = `PostToolUse` validators complete within a **60s** timeout; telemetry export interval **≤5s** (verify: REQ-OBS-002).
- **PD-5:** Data retention = evidence artifacts and traceability links retained per policy in the durable store, linked to commit SHAs (verify: REQ-STORE-002).

### 4.3 Value-Driven Deliverables (security assertions, cryptographic constraints, availability, deterministic success)
- **VD-1:** Enforcement-source assertion — **completion is decided only by deterministic gates from facts; no prediction or self-assessment can gate** (verify: Z3 CHECK-5 = unsat; REQ-STEER-006, REQ-PRED-002).
- **VD-2:** Provenance — signed SLSA build provenance on every merged artifact, externally verifiable (verify: REQ-SEC-003).
- **VD-3:** Internal-consistency assertion — the requirement set is contradiction-free and vacuity-free (verify: Z3 CHECK-1..4 all match; harness exit 0).
- **VD-4:** Fail-closed availability of the gate — ambiguity resolves to "blocked," gate is non-bypassable by config (verify: REQ-GATE-005).
- **VD-5:** Deterministic success criterion — a run is COMPLETE **iff** every in-scope requirement is `proven` with attached evidence and all gates pass; otherwise it is RUNNING or HANDOFF, never COMPLETE.

---

## STEP 5 — Adversarial Review Workflow (Draft → Red-Team → Correct)

### 5.1 Draft
The integrated PRD (Steps 1–4) was drafted mapping the 18-item domain baseline → 18 user stories → ~70 EARS requirements → real Z3 verdicts → bucketed deliverables.

### 5.2 Red-Team Critique (5 vectors) and 5.3 Corrections (applied)
1. **Completeness — did any baseline item slip through unmapped?**
   *Flaw found:* the first draft lacked an explicit requirement to *fail* on an unmapped baseline item (discovery could silently under-propose). **Correction applied:** added **REQ-SPEC-011** (IF any baseline item has zero proposed requirements THEN flag `UNMAPPED` and block advancement). Matrix now shows zero `UNMAPPED`.
2. **Acceptance-criteria rigor — any vague words ("fast", "secure", "optimized")?**
   *Flaw found:* early NFR phrasing used "fast/secure." **Correction applied:** added **REQ-SPEC-002** (reject non-deterministic adjectives lacking numeric bounds) and replaced all vague terms with deterministic bounds in §4.2 (coverage 85%, cap 25, retries 3, loop 7, timeout 60s, export ≤5s, 0 HIGH/CRITICAL findings).
3. **Traceability — can every Z3 assertion trace to a user story?**
   *Flaw found:* CHECK-3 (cap-vs-block) and CHECK-5 (prediction independence) had no explicitly linked requirement in the draft. **Correction applied:** bound CHECK-3 → REQ-LOOP-002 (US-13) and CHECK-5 → REQ-STEER-006 / REQ-PRED-002 (US-12/US-18); each table row in §3.3 now references its requirement.
4. **Executor-guardrail soundness — enough constraint to prevent architectural drift?**
   *Flaw found:* the draft asserted "PostToolUse blocks" (an overclaim that would mislead the executor into relying on it to prevent bad writes). **Correction applied:** **REQ-STEER-002** now states PostToolUse *cannot undo* and is a next-turn forcing function; **PreToolUse** is the sole prevention gate (REQ-STEER-003, REQ-HITL-001). Also added REQ-STEER-004 (command-type hooks fail closed; HTTP/MCP fail open) so the executor wires hard policy correctly.
5. **Deliverable clarity — are end-states ambiguous?**
   *Flaw found:* "done" and "stopped" were conflated; an executor could mark a cap-terminated run COMPLETE. **Correction applied:** **VD-5** defines COMPLETE iff all proven + gates pass; **REQ-LOOP-002** makes HANDOFF a distinct terminal state; Z3 CHECK-3 proves the two cannot collapse.

**Residual risks (honest, carried forward).** (a) OTel GenAI conventions are experimental and may rename attributes — pin versions (REQ-OBS-001). (b) Claude Code hook roster/semantics are version-gated (~27–30 events mid-2026) — re-verify against code.claude.com at build time. (c) The Z3 model is a bounded abstraction of critical invariants, not a proof of the full implementation — extend the harness as `feature_list.json` grows and run it as a required CI check. (d) Agent Teams and predictive routing are experimental/pre-product respectively — kept off the gating path by REQ-ORCH-003 and REQ-PRED-002.

### 5.4 Gap-closure corrections (applied after extended Z3 analysis — 21/21 checks)

The following three gaps were identified in an independent audit and closed with new requirements, each formally verified by extended harness checks:

1. **Domain-baseline checklist sourcing — REQ-SPEC-013..015 added.**
   *Gap:* REQ-SPEC-010 referenced "a curated domain-baseline checklist" with no answer for where it comes from, who produces it, or how it is versioned. Discovery was only as good as an artifact with no managed source.
   *Fix:* Added REQ-SPEC-013 (research sub-agent drafts checklist on first encounter, human reviews before use), REQ-SPEC-014 (checklists are version-controlled artifacts that accumulate across projects), REQ-SPEC-015 (checklist version is linked to `feature_list.json` for auditability). CHECK-9c verifies the UNMAPPED gate and completion gate are independent.

2. **Evidence schema — REQ-COV-006 added.**
   *Gap:* REQ-COV-003 said "require attached evidence" but left the schema to executor interpretation, making SubagentStop validation inconsistent.
   *Fix:* REQ-COV-006 defines a four-field evidence record: `test_file`, `test_name`, `output_hash`, `collected_at`. CHECK-7a proves PASSED without `output_hash` is UNSAT. CHECK-7c proves PASSED with zero evidence fields is UNSAT. CHECK-7b proves the rule is not vacuous.

3. **No-progress predicate operationalized — REQ-LOOP-002 refined.**
   *Gap:* REQ-LOOP-002 said "no-progress condition" in words only. A Stop hook implementation required a measurable predicate.
   *Fix:* No-progress is now defined as: zero items flipped `unproven→proven` AND zero commits produced, both across the last N consecutive slices (DEFAULT N=3). CHECK-8a/8b verify the operationalized predicate fires correctly and routes to HANDOFF.

4. **Scope-sequencing gate — REQ-EXEC-005 added.**
   *Gap:* The Stop hook blocked termination while any item was unproven, but nothing explicitly blocked *starting a new slice* while a prior item remained unproven. An agent could begin work on item N+1 before item N was verified.
   *Fix:* REQ-EXEC-005 adds a PreToolUse hook on WorktreeCreate/slice-assignment that blocks new slice initiation while any prior item is unproven. CHECK-6a proves newSliceStarting ∧ priorItemUnproven is UNSAT. CHECK-6b proves the rule is not vacuous.

---

## Appendix A — Verification & Acceptance Mapping (summary)
- **Logic model:** `formal_verification.py` (Z3 v4.16.0) — 21/21 checks, exit 0 = pass. Re-run in CI. Extended checks cover: CHECK-6 (scope-sequencing gate REQ-EXEC-005), CHECK-7 (evidence schema REQ-COV-006), CHECK-8 (no-progress predicate REQ-LOOP-002 refinement), CHECK-9 (UNMAPPED advancement gate REQ-SPEC-011 / domain-baseline sourcing REQ-SPEC-013..015).
- **Runtime gates:** `PreToolUse` (prevent — includes slice-sequencing gate REQ-EXEC-005 and plan-approval gate REQ-HITL-001), `PostToolUse` (fix-next-turn), `SubagentStop` (evidence schema validation per REQ-COV-006), `Stop` (coverage) + OPA/Conftest required status check + GitHub ruleset.
- **Awareness:** OTel (experimental conventions, pinned) → Langfuse (MIT) default; requirement-ID Baggage; hook-decision events to the same trace.
- **Every requirement** is tagged [DET] or [PROB]; only [DET] requirements may gate.

## Appendix B — EARS Pattern Legend
Ubiquitous (`The system SHALL …`); Event-driven (`WHEN … THEN the system SHALL …`); State-driven (`WHILE … the system SHALL …`); Unwanted behaviour (`IF … THEN the system SHALL …`); Optional (`WHERE … the system SHALL …`).

## Appendix C — Honest Limits & Version-Gated Facts
OTel GenAI semantic conventions: **experimental ("Status: Development")** as of mid-2026 — not stable. PostToolUse: **cannot undo** an executed action. Arize Phoenix: **Elastic License 2.0** (source-available, not OSI, no hosted-service). PredictStream: **pre-product** (no shipping release) — use battle-tested predictive-routing primitives instead. Agent Teams: **experimental** — off the gating path. All numeric thresholds are DEFAULTs to confirm against the target environment. Verdicts in Step 3 are machine-checked by the cited harness; re-run before relying on them.
