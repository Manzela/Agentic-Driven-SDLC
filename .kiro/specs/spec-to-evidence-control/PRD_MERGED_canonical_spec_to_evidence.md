# Canonical PRD (Merged) — Spec-to-Evidence Coverage Control System (Claude Code Substrate)

**Status:** Merged canonical source. Supersedes `PRD_spec_to_evidence_coverage_control_system.md` (v2) and Kiro's updated PRD. Reconciles with the three spec artifacts `requirements.md`, `design.md`, `tasks.md`.
**Formal validation:** Unified harness `formal_verification_merged.py` (Microsoft Research **Z3 v4.16.0**) — **34/34 machine-checked assertions pass, exit 0** (14 core + 12 Kiro reproduced + 8 new gap-closure invariants); the harness now self-counts its assertion groups (14 core CHECK-1..5c + 12 Kiro CHECK-6a..9c + 8 new CHECK-10a..13b = 34). The earlier "21/21" figure was corrected to 32, then extended to **34** by the P3 market-research addendum (CHECK-13a/13b: omission-declaration gate) — the legacy `formal_verification.py` (which reported "21 checks") is **DEPRECATED** and must not be cited.
**Date:** June 15, 2026

> **Governing invariant (unchanged, load-bearing):** deterministic gates — Claude Code hooks, CI, OPA — decide whether delivery is complete, computed solely from verifiable facts. Model self-assessment and probabilistic predictions only inform; they never gate. *(Z3 CHECK-5 proves a prediction cannot change a gate decision.)*

---

## 0. What this document is, and how it was produced

This merge is the output of an adversarial audit of three Kiro-generated artifacts (`requirements.md`, 394 lines; `design.md`, 990 lines; `tasks.md`, 779 lines), cross-referenced against (a) the prior canonical PRD, and (b) a 16-category / 95-pain-point problem statement. The audit was non-biased in both directions: Kiro's work was credited where verified (its formal additions were independently re-run, not trusted), and over-claims were corrected. The artifacts are high quality and faithful to the verified architecture; the changes below close concrete gaps rather than rebuild.

### 0.1 Audit verdict on the three Kiro artifacts (honest summary)

**Genuinely strong / accepted as-is:** the 32-requirement EARS set (20 original + 8 Merge-Reconciliation additions + 4 P3-market-research additions) with a 32-term glossary and per-requirement baseline mapping; the full `feature_list.json` JSON Schema (with `EvidenceRecord`, `additionalProperties:false`, `sha256:` pattern); the 8-table Postgres schema (6 original + `requirement_versions` + `gate_audit_log`) with an `evidence_complete` CHECK; the 13-row hook-wiring table; four subagent definitions with permission scopes; the EARS→SMT translation table; the checklist-lifecycle state machine; the `plan-approved.json` SHA-binding to `feature_list.json`; the 30 numbered correctness properties; and the 57 tasks across five required phases (0–4) plus two optional phases (5–6). The audited facts are carried correctly: OTel conventions labeled experimental, `PostToolUse` cannot undo, Phoenix is ELv2, predictions never gate, `HANDOFF` distinct from `COMPLETE`.

**Findings corrected in this merge (concrete, not stylistic):**
1. **Stop-hook ↔ HANDOFF logic error (substantive).** In `design.md` (`evaluate_stop`) and `tasks.md` (task 5), reaching the iteration cap or no-progress predicate calls `return block(...)` (exit 2). But a `Stop` hook exit-2 *forces the agent to keep working* — the opposite of terminating to HANDOFF, and a latent infinite-block that the reentrancy guard only masks. **Correction (REQ-LOOP-005):** on cap/budget/no-progress the hook SHALL record `status=handoff` and **allow** termination (exit 0) while emitting the HANDOFF summary out-of-band; `decision:block` is reserved for the unproven-items case where continuation is actually wanted.
2. **`Phase 4` inconsistency across files.** `design.md` calls Phase 4 the optional Temporal/Inngest outer loop; `tasks.md` calls Phase 4 the property-based-test suite; `requirements.md` calls Temporal out-of-scope. **Correction:** Temporal/Inngest is **Phase 5 (optional)**; the PBT suite is **Phase 4**; all three files aligned.
3. **Requirements with no implementation task.** Requirement 15 (Orchestration) and Requirement 20 (Execution Bounds NFR) are referenced by no task; security criteria **17.2 (secrets-block)** and **17.4 (sandbox)** and wiring criterion **8.3 (integration-test evidence)** are untasked. **Correction:** tasks added (see §6).
4. **EARS sixth pattern mismatch.** The glossary lists a "Complex" pattern but the schema enum and validator handle only five. **Correction:** "Complex" treated as a documented composition of the five base patterns; schema/validator unchanged; glossary clarified.
5. **Count correction.** "21/21" → **32/32** → **34/34** in the unified harness (the reproducible total: 14 core + 12 Kiro reproduced + 8 new invariants — the P3 addendum added CHECK-13a/13b); the legacy `formal_verification.py` is deprecated.

### 0.2 The non-biased completeness conclusion

Against the 95 pain points, the three artifacts as submitted reach **full coverage on 11 of 16 categories** and **partial on 5** (see §7). This merge closes the partials with the minimum sufficient requirements (no gold-plating) and **explicitly scopes** the genuinely heavy items rather than pretending they are built — which is the only honest way to claim "100% addressed."

---

## 1. In-Scope / Out-of-Scope (explicit)

### 1.1 In scope (v1 — the system proactively addresses these by design)
Spec compilation to atomic EARS + acceptance criteria; proactive discovery with **researched, versioned, human-approved** domain-baseline checklists; bounded spec-completion loop judged by a non-LLM validator; default-unproven `feature_list.json` coverage model with a 4-field evidence schema and **requirement-amendment versioning**; bidirectional traceability in Postgres; one-slice-at-a-time execution in worktrees with a scope-sequencing gate; wiring verification as a first-class coverage type; a four-layer verification engine (**structural, semantic, behavioral, security**) **plus a performance/accessibility layer (new, REQ-VERIFY-007)**; an independent verifier; a fail-closed completion gate (Stop hook + OPA/Conftest + GitHub ruleset); session continuity with **resumed-state integrity checks**; OTel awareness with requirement-ID Baggage, hook-decision forwarding, and **reasoning-loop detection (new, REQ-OBS-006)**; deterministic mid-flight steering via hooks; anti-loopmaxxing with the corrected HANDOFF semantics; Claude Code subagent/hook orchestration with an **expanded capability-role taxonomy (new, REQ-ORCH-004)**; durable Postgres storage; SAST/secrets/SLSA security gates with sandboxing; a **tamper-evident, hash-chained gate-decision audit log (new, REQ-AUDIT-001..003)**; an **epistemic-integrity gate on the research subagent's sourced output (new, REQ-SPEC-017)**; and human-in-the-loop plan approval + PR review. *(P3 market-research additions, June 2026:)* **structured omission declaration** enforced at SubagentStop (Spec-Kit `[Gap]` pattern, REQ-SPEC-018, CHECK-13); **DeepEval eval-gating in CI** (`assert_test()`, REQ-EVAL-001); **OWASP ZAP baseline passive DAST scan** as required status check (REQ-SEC-008); **OpenFeature + flagd agent kill-switch** (self-hosted, ≤30 s propagation, REQ-CTRL-001).

### 1.2 Out of scope for v1 (explicitly deferred, with rationale — not silently dropped)
- **Predictive next-step routing (REQ-PRED-\*)** — kept *defined but optional/off-gate*; deferred to **Phase 6**. Rationale: it is an acceleration aid, must never gate, and depends on primitives (Speculative Actions, semantic-router, the Claude memory tool) better adopted after the deterministic spine is proven. *Pain points 2.9–2.11 are therefore PARTIAL-by-design.*
- **Temporal/Inngest durable outer loop** — **Phase 5, optional**; add only when multi-hour crash-durability is an observed need.
- **Agent Teams (peer-to-peer)** — off the gating path until it exits experimental status and supports resumption.
- **Full regulator-grade compliance tooling** (e.g., complete EU AI Act conformity packaging) — v1 ships the *technical substrate* (hash-chained audit log + SLSA provenance + evidence chain) that such compliance is built on; the legal conformity packaging itself is out of scope.
- **Cryptographic *correctness* proof of the implementation** — v1 provides formal proof of the *requirement logic model* (Z3) and tamper-evidence of the *execution record*; full deductive proof of arbitrary generated code is a research-grade goal, not v1.
- **Pact consumer-driven contract testing** *(P3 market-research deferral)* — no Tier-1 verified evidence of Pact fit with Claude Code hook/subagent boundaries; contract testing at the LLM output layer lacks an established standard. Revisit post-v1.
- **Runtime structured-output enforcement (Pydantic/BAML)** *(P3 market-research deferral)* — the SubagentStop gate (REQ-COV-006) already enforces Evidence_Record structure at the hook boundary; Pydantic/BAML adds coupling at call sites without closing a gap not already gated. Revisit if schema drift is observed.
- **promptfoo CI eval harness** *(P3 market-research deferral)* — DeepEval (Req 30) covers the v1 eval-gating need via pytest-native `assert_test()`; promptfoo adds a parallel YAML-based harness without incremental coverage in v1. Deferred to Phase 3+.

---

## 2. Requirements (merged set)

The 20 original requirements in `requirements.md` are adopted unchanged except where §0.1 corrects them. Requirements **21–28** (Merge Reconciliation Addendum) and **29–32** (P3 Market-Research Addendum) close audited gaps and add Tier-1 industry-standard capabilities, bringing the canonical total to **32 numbered requirements (Requirement 1–32; 20 original + 12 added)**; each added requirement is in EARS form with a `[DET]`/`[PROB]` label, and the logic-checkable ones cite their Z3 check.

- **REQ-LOOP-005 [DET]** (Unwanted): IF the iteration cap, cost budget, or no-progress predicate is reached, THEN the Stop hook SHALL set `run_state.status=handoff`, emit the HANDOFF summary, and **ALLOW termination (exit 0)** — it SHALL NOT `block`/exit-2 (which would force continuation). *(Corrects the design bug in §0.1-1.)*
- **REQ-COV-007 [DET]** (Unwanted): IF a requirement is amended after approval, THEN its coverage item SHALL re-enter `unproven` (a new version), and the deliverable SHALL NOT be COMPLETE while any amended item is un-reproven. A `requirement_versions` record SHALL capture prior text, new text, author, timestamp, and rationale. *(Z3 CHECK-10a/10b.)*
- **REQ-STATE-005 [DET]** (Unwanted): IF a session resumes AND the resumed-state hash does not match the durable store's recorded hash, THEN the System SHALL block the run from proceeding and require operator reconciliation (guards against false/corrupted resumption). *(Z3 CHECK-11a/11b.)*
- **REQ-SPEC-016 [DET]** (Unwanted): IF a domain-baseline checklist is in DRAFT (not human-approved), THEN it SHALL NOT be used for discovery. *(Z3 CHECK-12a/12b; formalizes the lifecycle rule already in `design.md`.)*
- **REQ-SPEC-017 [DET]** (Event-driven): WHEN the Research_Sub_Agent drafts a domain-baseline checklist or any sourced claim, THEN every external claim SHALL carry a source URL, each source SHALL be labeled by authority tier (primary/standard/peer-reviewed vs blog/vendor/social), and an independent fact-check pass SHALL flag unverifiable or low-authority-only claims before human review. *(Directly imports this project's own epistemic-integrity standard; closes pain-point category 15 for sourced content.)*
- **REQ-VERIFY-007 [DET]** (Event-driven): WHEN an NFR coverage item of subtype `performance` or `accessibility` is verified, THEN the System SHALL run the corresponding tool with a numeric budget — performance via k6/Lighthouse (e.g., p95 latency, Core Web Vitals thresholds), accessibility via axe-core (zero WCAG-A/AA violations on covered screens) — and attach the result as the Evidence_Record. *(Closes the performance/accessibility gap; these were named in pain-point category 3.)*
- **REQ-VERIFY-008 [DET]** (Ubiquitous): The System SHALL treat **UI-screen completeness** as a distinct WIRING-adjacent verification target: every screen/state declared in the coverage model (including empty, loading, and error states) SHALL have a behavioral test asserting it renders. *(Closes pain-point 1/4 "missing screens you didn't know to test.")*
- **REQ-OBS-006 [DET]** (Event-driven): WHEN telemetry is analyzed, THEN the System SHALL emit a `REASONING` span kind and SHALL flag repeated-action / reasoning-loop patterns (e.g., identical tool-call signatures recurring ≥ K times) as a first-class signal, complementing the slice-level no-progress watchdog. *(Closes pain-point 7 "reasoning loops invisible to standard tracing"; grounded in the AgentTelemetry finding.)*
- **REQ-AUDIT-001 [DET]** (Ubiquitous): The System SHALL append every gate decision (event, tool, allow/block, reason, requirement ID, actor agent, timestamp) to a **hash-chained, append-only audit log** where each entry stores the hash of the prior entry. *(Tamper-evidence of the full session, not just final state — pain-point category 9.)*
- **REQ-AUDIT-002 [DET]** (Event-driven): WHEN the audit log is verified, THEN any entry whose stored prior-hash does not equal the recomputed hash of the preceding entry SHALL fail verification (tamper detection).
- **REQ-AUDIT-003 [DET]** (Ubiquitous): The System SHALL sign build artifacts with SLSA provenance (existing REQ-SEC-003) AND retain the hash-chained gate-decision log as the execution-proof complement, so "we can prove what happened" is distinct from and additional to "the trace says what happened."
- **REQ-ORCH-004 [DET]** (Optional): WHERE a project requires capability roles beyond planner/implementer/verifier/research, THE System SHALL support additional bounded subagent roles — **design** (UI/UX + component choices), **platform** (IaC/deploy/env), and **reliability** (SLO/chaos) — each with an explicit permission scope and none with verifier write access. *(Closes the role-taxonomy gap, pain-point category 11; OPTIONAL so v1 is not over-built.)*

**Adopted requirement→baseline matrix:** the `requirements.md` Appendix matrix (B01–B19, zero `UNMAPPED`) is adopted, extended with the added requirements above mapped to their categories.

---

## 3. Formal Verification (unified)

`formal_verification_merged.py` (Z3 v4.16.0) **self-counts its assertion groups** and runs **34 machine-checked assertions, all passing (exit 0)** — the harness emits the live total at the end of its run so the count can never drift from the spec:
- **14 core** (CHECK-1..5c family): core consistency SAT; maintenance-vs-admin-save conflict UNSAT→corrected SAT; cap-vs-completion conflict UNSAT→corrected SAT (justifies HANDOFF); vacuity/liveness; prediction-cannot-gate UNSAT.
- **12 Kiro** (CHECK-6a..9c family), independently re-derived and reproduced: scope-sequencing gate; 4-field evidence schema; no-progress predicate → HANDOFF; UNMAPPED blocks advancement.
- **8 new** (CHECK-10a..13b): amendment monotonicity (amended-not-reproven cannot be COMPLETE); resumed-state integrity (hash mismatch cannot proceed); checklist-approval-before-use (DRAFT cannot be used); omission-declaration gate (null `omission_declaration` cannot be accepted — P3, CHECK-13a/13b).

The legacy `formal_verification.py` (which reported "21 checks") is **DEPRECATED**; only `formal_verification_merged.py` and its self-counted 34 are canonical.

Honest limit (carried forward): Z3 verifies the **logic model**, not the implementation. The harness is a required CI check and must be extended as `feature_list.json` grows; tamper-evidence (REQ-AUDIT-\*) is a runtime property checked by the chain verifier, not by Z3.

---

## 4. System Design & 5. Architecture

Adopted from `design.md` (system-context + execution-loop diagrams; 26-component inventory with file paths/phases; `feature_list.json` schema; 8-table Postgres schema; hook-wiring table; subagent definitions; EARS→SMT approach; checklist lifecycle; Phase-0 spine list; no-progress watchdog; `plan-approved.json` gate), with these merge deltas (vs the pre-merge design): the Stop-hook HANDOFF path corrected per REQ-LOOP-005; a `requirement_versions` table added (REQ-COV-007); a `gate_audit_log` hash-chained table added (REQ-AUDIT-001/002); a resumed-state hash check added to `SessionStart` plus a PreToolUse integrity guard (REQ-STATE-005); a `REASONING` span attribute on an INTERNAL span added to observability (REQ-OBS-006); and performance/accessibility/UI-completeness verification added to the verifier (REQ-VERIFY-007/008). Phase numbering corrected: Phase 4 = PBT suite; Phase 5 = optional Temporal/Inngest; Phase 6 = optional predictive routing.

---

## 6. Tasks (reconciled)

Adopted from `tasks.md` (53 tasks across five required phases (0–4) plus two optional phases (5–6); 1–42 original + 43–53 added) with these additions/corrections: task added for **Requirement 15** (establish subagent/hook inner orchestration explicitly + Phase 5 Temporal stub behind a flag); task added for **Requirement 20** (centralize the numeric thresholds as configurable defaults with override checks); tasks added for **17.2 secrets-block** and **17.4 sandbox** (e.g., Claude Code sandbox / E2B / devcontainer) and **8.3 WIRING integration-test evidence**; the Stop-hook task corrected to the REQ-LOOP-005 allow-on-HANDOFF semantics; new tasks for REQ-COV-007, REQ-STATE-005, REQ-SPEC-016/017, REQ-VERIFY-007/008, REQ-OBS-006, REQ-AUDIT-001..003, REQ-ORCH-004, each with a matching correctness property; and Phase numbering aligned with §4.

---

## 7. Coverage Matrix — 95 Pain Points × 16 Categories (the completeness proof)

Legend: **C** = covered in v1 in-scope; **P** = partial / closed-by-this-merge or deferred-by-design (noted); **—** = was missing, now closed by a named requirement.

| Cat | Pain points | Status | Where addressed / how closed |
|-----|-------------|--------|------------------------------|
| **1. Agent Execution & Completeness** (8) | missing components/states/handlers; structural-but-unwired; premature self-completion; can't trust completion; confidence≠evidence; long-run drift; green-tests≠fulfillment; repeated human pointing | **C** | Coverage model (R5), Stop gate (R10), independent verifier (R9), wiring (R8) + **UI-completeness (REQ-VERIFY-008)**, no-progress watchdog (R14), evidence-based proof (R5.3/COV-006), durable coverage model removes repeat-pointing |
| **2. Context & Session Continuity** (11) | context degradation; no cross-session memory; **false/corrupted resumption**; mid-run crash; resume exactly; position vs goal; **business-ID propagation**; manual recompile; **where-to-look-next**; token bloat; **predictive context** | **P** | PreCompact/SessionStart/durable state (R11), requirement.id Baggage (R6.4/R12.4); **false-resumption now closed by REQ-STATE-005**; *where-to-look-next + predictive-context + token-routing are PRED-\*, deferred to Phase 6 by design (1.2)* |
| **3. Specification & Requirements** (5) | NL not machine-checkable; non-atomic; no enforced format; **NFRs (incl. accessibility, performance) late/absent**; acceptance not normalized | **C** | EARS + Z3 (R1/R4), atomic IDs (R1.1), NFR first-class (R5.4); **performance + accessibility now closed by REQ-VERIFY-007** |
| **4. Coverage & Traceability** (7) | no unified model; no req→code→test map; can't query covered/not; wiring not a target; arch vs surface; multi-agent handoff breaks chain; **per-agent decision attribution** | **C** | feature_list.json (R5), bidirectional links (R6), wiring (R8), subagent identity in evidence + audit actor (REQ-AUDIT-001), Property 24 role separation |
| **5. Quality Gates & Completion** (5) | no fail-closed gate; self-report/green-tests; vague "done"; exists vs behaves vs wired; gate decisions not in trace | **C** | Completion gate (R10), VD-5 definition, evidence-based (R5), hook decisions in trace (R12.3) |
| **6. State & Artifact Durability** (4) | transient-only state; matrices not authoritative; git not used as trail; no durable cross-session state | **C** | Durable artifacts + Postgres (R11/R16), commit-per-slice trail (R11.4) |
| **7. Observability & Debuggability** (7) | no real-time view; reasoning invisible; **reasoning loops undetectable**; silos; passive/retrospective; trace↔gates disconnected; agent self-correct telemetry | **C** | OTel live + requirement-tagged (R12), hook decisions co-located (R12.3); **reasoning-loop detection now closed by REQ-OBS-006**; active hooks ≠ passive; self-correction intentionally not on gate path |
| **8. Enforcement & Invariants** (7) | no deterministic prevention; after-the-fact checks; reason-around soft guardrails; prompt≠enforcement; no force-to-done; wiring/structural breakage uncaught; sub-agent accepted without evidence | **C** | PreToolUse prevention (R13.2/3), command-hooks fail-closed (R13.4), Stop forces continuation (R10.2), SubagentStop evidence (R9.5) |
| **9. Auditability & Proof** (9) | **tamper-evident exec proof**; trace says vs prove; auditor demonstration; **prove invariants across full session**; continuous compliance; **EU AI Act logs**; crypto-proof vs correctness-proof; formal proofs only academic; startups early | **P→C(substrate)** | SLSA provenance (R17.3), Z3 logic proof; **hash-chained gate-decision audit log now closed by REQ-AUDIT-001..003** (full-session tamper-evidence); *legal EU AI Act conformity packaging explicitly out-of-scope (1.2) — substrate provided* |
| **10. Human-as-Infrastructure** (7) | external memory; external verifier; micro-steering ∝ length; humans can't track all; reactive review; minutes-not-ms; no auto-correction | **C** | Coverage model = external memory, gates = external verifier, plan-approve-once (R18), ms-latency hooks vs dashboards |
| **11. Agent Organization & Role Structure** (3) | no reusable role pattern; planner/implementer/verifier underspecified; **no capability categories (product/design/platform/reliability/security/QA)** | **C** | 4 subagents with permission scopes (design.md); **design/platform/reliability roles now closed by REQ-ORCH-004 (OPTIONAL — not over-built)** |
| **12. Execution Scope & Decomposition** (4) | oversized tasks; weak one-slice enforcement; unbounded task boundaries; no commit-to-one-unit | **C** | One-item/session (R7.1), worktrees (R7.2), scope-sequencing gate (R7.5), atomic commits (R7.3) |
| **13. Passive Execution & Domain-Baseline Blindness** (3) | passive only; misaligned with domain standards; not tier-1 production-grade | **C** | Proactive discovery (R2) + researched/versioned/approved checklists (R3/B19), tier-1 via baseline completeness |
| **14. Framework, Runtime & Stack Selection** (4) | biased tool choice; no systematic comparison; orchestration/memory/runtime uncertainty; **benchmark-vs-production gap** | **P** | Stack choices made + first-principles comparison in the reference-architecture doc (Claude Code, Neon, Langfuse, Semgrep/CodeQL/SonarQube, Playwright, OPA, hypothesis); *the comparison rationale lives in the reference architecture, referenced here; "benchmark-vs-production gap" is a known risk, mitigated by evidence-based gating rather than benchmarks* |
| **15. Epistemic Integrity & Self-Report Unreliability** (5) | fabricated citations; self-content needs adversarial check; agreement bias; **self-report≠evidence**; **low-authority sources unlabeled** | **C** | Self-report≠evidence is the system's core (independent verifier, evidence gates, predictions don't gate); **research-subagent citation/authority/fact-check now closed by REQ-SPEC-017** |
| **16. Market & Structural Gaps** (6) | no single product does observe+enforce+prove; passive-vs-active boundary unrecognized; key gaps user-built; long-run session mgmt; **no vendor-neutral schema**; proof-layer startups early | **C(design intent)** | The system integrates all three planes (observe R12 + enforce R13 + prove REQ-AUDIT-\*); passive/active boundary is explicit; feature_list.json + EvidenceRecord + requirement.id Baggage constitute the vendor-neutral "what/which-requirement/outcome" schema |

**Coverage result:** of 16 categories, **12 fully covered in v1**, **4 partial** — and every partial is either **closed by a named new requirement** (2→REQ-STATE-005; 3→REQ-VERIFY-007; 7→REQ-OBS-006; 9→REQ-AUDIT-\*; 11→REQ-ORCH-004; 15→REQ-SPEC-017) **or explicitly deferred with rationale** (predictive-context routing in cat 2 → Phase 6; EU AI Act legal packaging in cat 9 → out-of-scope; benchmark-vs-production in cat 14 → mitigated by evidence-gating). No pain point is silently unaddressed.

---

## 8. Deliverable Buckets

Adopted from the prior PRD §4 (User-/Product-/Value-Driven), extended: **VD-6** tamper-evident gate-decision audit log verifiable by the chain verifier (REQ-AUDIT-002); **PD-6** performance/accessibility budgets (p95, Core Web Vitals, zero WCAG-A/AA violations) as Evidence_Records (REQ-VERIFY-007); **UD-5** every declared screen/state has a render assertion (REQ-VERIFY-008).

---

## 9. Adversarial Review (this merge)

**Vector — completeness:** all 95 pain points mapped (§7); 0 silently unaddressed. **Vector — over-engineering (explicit "0% over-engineering" bar):** the expanded role taxonomy (REQ-ORCH-004), Temporal (Phase 5), and predictive routing (Phase 6) are all OPTIONAL/deferred so the v1 spine stays minimal; heavy items (full EU AI Act packaging, code-correctness proofs) are scoped out with rationale rather than gold-plated. **Vector — traceability:** every new requirement carries a Z3 check or a named verification tool; every Z3 assertion (34, self-counted as 14 core + 12 Kiro reproduced + 8 new) reproduces. **Vector — executor-guardrail soundness:** the Stop-hook HANDOFF bug is corrected (REQ-LOOP-005) so the loop actually halts to a human instead of force-continuing. **Vector — deliverable clarity:** COMPLETE vs HANDOFF remains mutually exclusive (CHECK-3); amendments re-enter unproven (CHECK-10).

## 10. Honest Limits
OTel GenAI conventions experimental (pin/opt-in); Claude Code hook roster version-gated (~27–30, re-verify); `PostToolUse` cannot undo; Z3 proves the logic model not the implementation; tamper-evidence is runtime, not Z3; performance/accessibility/audit-log requirements are specified here and tasked, with implementation in their phases; all numeric thresholds are configurable DEFAULTs. Re-run `formal_verification_merged.py` (34/34, self-counted) before relying on the formal claims; the legacy `formal_verification.py` is deprecated and must not be cited.
