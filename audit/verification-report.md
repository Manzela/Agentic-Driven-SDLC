# Verification Report — Spec-to-Evidence Control System

**Date:** 2026-06-15
**Method:** `superpowers:verification-before-completion` discipline (evidence before claims). Independent ground-truth pass (direct file reads + grep + **executing the Z3 harness**, z3 4.16.0 → `34/34`, exit 0) followed by a 65-agent parallel audit workflow (6 finder axes → adversarial verification → synthesis), cross-checked against live file contents only.
**Result:** **77 raw findings → 58 verified → 57 confirmed, 0 refuted (zero false positives), 19 P2/P3.** Severity: 21 P0 · 35 P1 · 1 P2.
**Verdict:** The spec artifact set is **NOT complete and NOT internally consistent.** `audit/reconciliation-report.md` is an abandoned/false completion claim. The Z3 harness (34, self-counting) + `README.md` are the only current layer; the spec triad and audit trail have drifted.

> This report supersedes the stale `audit/findings.md` and `audit/reconciliation-report.md`, which were written against a larger "canonical merged" copy (`PRD_MERGED_canonical_spec_to_evidence.md`) that **does not exist** anywhere in this repo or its siblings, and which cite line numbers beyond the actual file EOFs.

---

# Verification Synthesis: spec-to-evidence-control Artifact Set — Authoritative Remediation Report

## 1. Verification Verdict

**The spec artifact set is NOT complete and NOT internally consistent.** It exhibits multi-layered version drift across four strata that never reconciled: (a) a **current layer** — `verification/formal_verification_merged.py` (self-counting, 34 assertions, verified by direct execution: `Result: 34/34 checks passed`, exit 0, Z3 4.16.0) and `README.md` (already synced to 34) — these two are the *only* trustworthy current artifacts; (b) a **stale pre-merge layer** — `requirements.md` (20 requirements, "21/21 assertions", cites the deprecated `formal_verification.py`) and `design.md` (24 properties, 6 tables, "five build phases", "21 such checks", deprecated harness); (c) a **mid-merge layer** — `tasks.md` (internally self-contradictory: "29" vs "24"; references tasks 32a/32b/32c and requirements 21–27 that do not exist in `requirements.md`; wave graph stops at 36 waves and omits 11 leaf tasks); and (d) a **false-claim audit layer** — `audit/reconciliation-report.md` asserts a fully-reconciled state ("32/32, 28 requirements, 8 tables, 45 waves, Properties 25-29 authored") that is **false on disk in every cell**, directly contradicting `audit/audit-plan.md` ("No fixes applied"); both audit files plus `findings.md` cite line numbers beyond EOF and a `PRD_MERGED_canonical_spec_to_evidence.md` that **does not exist anywhere**. The headline: **the harness (34) is the authoritative oracle, README mirrors it, and everything else has drifted — the reconciliation-report is an abandoned/false completion claim, not evidence.** Beyond pure drift, the verification surfaced **real logical defects** the harness was written to forbid but the design reference code still contains (the infinite-block HANDOFF bug, F-LOGIC-01) and **chain breaks** where harness-proven invariants (CHECK-10/11/12/13, Properties 25–30) have no requirement, no design property, and no wave-scheduled task.

---

## 2. Canonical Target Values

Every file must converge on these single values. Arithmetic is shown so the targets are auditable. The convention chosen (and recommended): **harness-proven invariants become new acceptance criteria under the nearest existing requirement** (extending its `REQ-xxx-NNN..M` range), except the audit-log family and research-claim labeling, which have no existing home and become **new requirement headings**.

| Metric | Current (drifted) values on disk | **CANONICAL TARGET** | Arithmetic / derivation |
|---|---|---|---|
| **Z3 harness checks** | 21 (req/design), 29 (tasks), 32 (audits) | **34** | Self-counted: `TOTAL = checks_run`. core-14 (CHECK-1..5c) + Kiro-12 (CHECK-6a..9c) + new-8 (CHECK-10a..13b) = **34**. Verified by execution, exit 0. Never hardcode. |
| **Requirements (`### Requirement` headings)** | 20 (req), "28" claimed (recon) | **22** | 20 existing + **2 new headings**: Requirement 21 = Audit-Log Tamper Detection (REQ-AUDIT-001..003), Requirement 22 = Research-Claim Authority Labeling (REQ-SPEC-017). The other 5 net-new invariants are **acceptance criteria under existing requirements**, not new headings (see below), so they do NOT add headings. |
| **Acceptance-criteria additions (no new heading)** | — | **+6 criteria** | Req 5 +1 (REQ-COV-007, amendment monotonicity); Req 11 +1 (REQ-STATE-005, resumed-state integrity); Req 3 +1 (REQ-SPEC-016, checklist-approval); Req 9 +2 (REQ-VERIFY-007/008, perf-a11y + UI-completeness) **or** +1 (REQ-SPEC-018 omission gate — see Class-B); Req 14 +1 (REQ-LOOP-005, HANDOFF-exits-0). REQ-SPEC-018 homing is a Class-B decision (Req 9 vs new spec req). |
| **Correctness Properties (`### Property N`)** | 24 (design), "29" claimed (recon/tasks) | **30** | 24 existing + Property 25 (Amendment Monotonicity), 26 (Resumed-State Integrity), 27 (Checklist-Approval), 28 (Audit-Log Tamper Detection), 29 (Research-Claim Labeling), 30 (Omission-Declaration Gate). = **30**. Note: harness comment already names "Property 30" for CHECK-13. |
| **Property↔check mapping** | inconsistent | 25→CHECK-10a/10b, 26→CHECK-11a/11b, 27→CHECK-12a/12b, 30→CHECK-13a/13b; 28 (audit-log) & 29 (research-claim) have **no harness check yet** (Class-B: add CHECK-14 or leave PBT-only) | 4 families × 2 = 8 new checks already in harness; 28/29 are PBT-only unless CHECK-14 authored |
| **Top-level tasks (`- [ ] N.`)** | max = 42 | **42** (unchanged) + sub-tasks 32a/32b/32c | No tasks 43–53 exist; the recon "53" is fabricated. Net-new work lives as 32a/32b/32c sub-tasks and 39.15/39.16, not new top-level numbers. |
| **Dependency-graph waves** | 36 (ids 0–35) | **≥ 36, all 11 orphan leaves scheduled** | Recon "45 (0–44)" is fabricated. Must add: 28.8, 28.9, 32a.1, 32a.2, 32b.1, 32b.2, 32b.3, 32c.1, 32c.2, 39.15, 39.16 = **11 leaves** currently absent. Final wave count is whatever closes the graph (≥ 36; renumber or non-contiguous insert). |
| **Postgres tables / `CREATE TABLE`** | 6 (design), "8" claimed (recon), 8 migrations (tasks) | **8** (if migrations 007/008 kept) or **6** (if 007/008 dropped) — **Class-B** | design.md has 6; tasks.md references migrations 001–008 (28.7=requirement_versions, 28.8=gate_audit_log). Recommended: **8** (author the 2 CREATE TABLE blocks in design.md, flip "Six tables"→"Eight tables" at design.md:138, :405). |
| **Build-phase wording** | design "five build phases" / Phase 4 "(optional)" | **5 required phases (0–4) + 2 optional (5–6)** | Phase 4 = PBT suite (required); Phase 5 = Temporal/Inngest (optional); Phase 6 = predictive routing (optional). Matches tasks.md:5 and ROADMAP.md. |
| **Hooks** | tasks "five hooks" (×2) | **6** | PreToolUse, PostToolUse, Stop, SubagentStop, PreCompact, SessionStart (README.md:45, design.md:194-204). |
| **EARS patterns** | glossary "6" (incl. Complex) vs everywhere "5" | **5** | {ubiquitous, event-driven, state-driven, unwanted, optional}. Drop "Complex" + "Unwanted behaviour" wording at requirements.md:31. |
| **Status enum** | {unproven, proven, failed} but only unproven→proven writable | **{unproven, proven, failed} with unproven→failed permitted** — **Class-B** | Either allow verifier `unproven→failed` transition (preferred) or drop `failed` from enum (design.md:355/424, tasks.md:27). |
| **Canonical PRD** | `PRD_MERGED_canonical_spec_to_evidence.md` cited by 3 audits | **does not exist** | Strip all `PRD_MERGED:N` citations (findings.md:5/38/39, reconciliation-report.md:10, audit-plan.md:19) OR author the file. |

**Requirements arithmetic, explicit:** `20 (existing) + 2 (REQ-AUDIT family heading + REQ-SPEC-017 research-claim heading) = 22 headings`. The 5 other net-new REQ IDs are absorbed as acceptance criteria under Req 3/5/9/11/14, raising those requirements' internal `..NNN` ranges but not the heading count. If the Class-B decision instead promotes REQ-SPEC-018/016 to standalone headings, recompute; the recommended default is 22.

---

## 3. Deduplicated Findings (merged across axes)

Findings that multiple axes independently confirmed are merged with a **[confidence: N axes]** note. Severity reflects the highest assigned across merges.

### P0 — Blocking (false claims, infinite-block defect, broken chains, count lies)

**P0-1 · Harness count is 34, not 21/29/32 — every other file is stale** [confidence: 6 findings: F-COUNT-01/02/03, F-COUNT-01(audit), F-REQ-01/02, F-PROP-CONTRA-2429]
- **Evidence:** `requirements.md:9` & `:358` = "21/21"; `design.md:547` "21 such checks", `:588` "all 21 checks pass", `:778` "all 21 PRD checks"; `tasks.md:91/258/301` "29"; `audit/findings.md:20/31/130` "32/29"; `reconciliation-report.md:16` "32". Oracle: `formal_verification_merged.py:506` `TOTAL = checks_run` (currently 34), executed → `34/34`, exit 0. `README.md:41` already = 34.
- **Canonical:** 34.
- **Remediation:** `requirements.md:9` 21/21→34/34; `:358` 21/21→34/34 + filename fix; `design.md:547` 21→34, `:588` 21→34, `:778` 21→34; `tasks.md:91/258/301` 29→34 (NOT :619, which is the property count). Do not hardcode where the source self-counts.

**P0-2 · Deprecated harness filename `formal_verification.py` cited as live oracle** [confidence: 4: F-COUNT-12, F-DSGN-01, F-DSGN-04, F-REQ-01]
- **Evidence:** `requirements.md:358`, `design.md:547`, `design.md:588` cite `formal_verification.py` as the passing harness. The only live harness is `verification/formal_verification_merged.py`; the bare file exists only at `docs/superseded/formal_verification.py` (deprecated; its own header admits it "executes 23 check() calls but hardcodes total=21").
- **Canonical:** `verification/formal_verification_merged.py`.
- **Remediation:** Repoint exactly **three** live references (358/547/588). `design.md:778` references `tests/unit/test_spec_validator.py` (a test file, not the harness) — fix only its "21" count, leave the filename.

**P0-3 · `reconciliation-report.md` is a false completion claim** [confidence: 5: F-RECON-02/03/04/05, F-CONTRA-01, F-COUNT-08]
- **Evidence:** Claims on disk vs reality: `:16` "32/32, no live 29/29" (live: 34; "29" persists at tasks.md:91/258/301/619); `:18` "28 requirements" (live: 20); `:22` "8 tables / no live six tables" (live: 6 `CREATE TABLE`; design.md:138/:405 still say "six/Six tables"); `:20` "45 waves (0–44), tasks 43–53" (live: 36 waves ids 0–35; no tasks 43–53); `:24` "deprecation-only, no live 21/21" (live: requirements.md:9/358 + design.md:547/588 carry "21/21" with NO deprecation banner anywhere); `:5` "fixes applied / back-propagated" contradicts `audit-plan.md:3` "No fixes applied". `grep` for "Reconciliation 2026|32/32|34/34|28 Requirement|eight tables|deprecat" over the three spec docs = ZERO hits.
- **Canonical:** Spec docs are UNRECONCILED; the report is aspirational, not factual.
- **Remediation:** Rewrite as an **"INTENDED reconciliation — NOT YET APPLIED"** design-decision record with a status banner; correct its own stale "32/32"→"34/34"; strip the non-existent `PRD_MERGED` reference (`:10`); reconcile `audit-plan.md:3`'s blanket "No fixes applied" to note the two partial fixes that DO exist on disk (the deprecation banner in `docs/superseded/formal_verification.py`; the self-counting merged harness).

**P0-4 · Audits ran against a phantom larger copy — citations beyond EOF** [confidence: 3: F-PHANTOM-01, F-PHANTOM-02, F-CANON-01]
- **Evidence:** `design.md` = 990 lines; `requirements.md` = 394 lines. `audit-plan.md:19/34/42` cite `design.md:1052/1024-1037/1044`; `findings.md:41/61/90/116/130` cite `design.md:1052/1009/1025/1048`, `findings.md:40` cites `requirements.md:400` — all past EOF. `find -iname '*PRD_MERGED*'` = 0 files, yet cited at `findings.md:5/38/39`, `reconciliation-report.md:10`, `audit-plan.md:19`.
- **Canonical:** Only the 990/394/913/522-line files exist; no `PRD_MERGED`.
- **Remediation:** Regenerate `findings.md` and `audit-plan.md` against live files; delete every beyond-EOF citation and every `PRD_MERGED:N` reference; correct headline count to 34.

**P0-5 · Infinite-block defect: reference `evaluate_stop` returns `block()` (exit 2) on HANDOFF paths** [confidence: 1: F-LOGIC-01, the single most severe logical defect]
- **Evidence:** `design.md:649-650` (no-progress) and `:655-656` (cap) both `return block(...)`. This is the exact infinite-block bug the harness forbids: `formal_verification_merged.py:151-154` core_axioms force `Or(capReached,budgetExceeded,noProgress) → Not(hookExitsBlocking)`; CHECK-5b (266-269), 5c (272-275), 8c (364-370) prove blocking-on-cap/no-progress is UNSAT. Banner lines 20-24: "cap/no-progress ALLOWS termination (exit 0), never blocks (exit 2). Fixes latent infinite-block defect."
- **Canonical:** HANDOFF paths must `allow()` (exit 0); only the unproven-items branch blocks.
- **Remediation:** `design.md:649-650` and `:655-656` → `return allow()`. Keep `write_run_state(status="handoff",...)` (already present at 648/654). Leave Check 1 / unproven branch as `block()`.

**P0-6 · Resumed-state integrity gate can never fire (REQ-STATE-005/CHECK-11)** [confidence: 2: F-LOGIC-02, F-COV-02]
- **Evidence:** CHECK-11a (`formal_verification_merged.py:451-455`) proves `resumeHashMismatch ∧ runProceeds` UNSAT — the gate must BLOCK. But task 32a wires the check into `session_start_hook.py` (`tasks.md:508`), and SessionStart is non-blocking everywhere: `design.md:203` "Nothing (informational load)", `tasks.md:164` "exit 0 always", `:165` "exit 0 (non-blocking)". A SessionStart hook cannot block a subsequent tool call, so the Z3-proven gate has no event that can enforce it.
- **Canonical:** Enforce at PreToolUse (the "sole true prevention gate", requirements.md:22).
- **Remediation:** Relocate `state_integrity.check()` into `pre_tool_use_hook.py`; update `tasks.md:508` and add a PreToolUse row at `design.md:203`. SessionStart may compute but not enforce.

**P0-7 · Dangling requirement citations: tasks.md cites Requirements 21–27 that do not exist** [confidence: 7: F-DANGLE-21/22/23/24/25/27, plus F-DANGLE-REQVERIFY/REQSPEC017]
- **Evidence:** `requirements.md` stops at Requirement 20 (`:345`). `tasks.md` `_Requirements:_` / `Validates:` lines cite **21.1** (`:112,:118`), **22.1** (`:451,:463,:718`), **23.1** (`:509,:513,:718`), **24.1/24.2** (`:541,:545,:718,:722`), **25.1/25.2/25.3** (`:216`), **27.1/27.2/27.3** (`:456,:463,:522,:527,:531`). All dangle. Harness canonical IDs: REQ-COV-007, REQ-STATE-005, REQ-SPEC-016, REQ-AUDIT-001..003, REQ-VERIFY-007/008.
- **Canonical:** Each token must point at a real requirement after the new IDs are authored.
- **Remediation (per token):**
  - `21.1` (tasks.md:112/118) → drop it; the invariant is already Requirement 14.2 (already cited on both lines). **Do not author a new Req 21 for this.**
  - `22.1` (amendment monotonicity) → author REQ-COV-007 as Req 5 criterion 7; repoint to `5.7`.
  - `23.1` (resumed-state) → author REQ-STATE-005 as Req 11 criterion 5; repoint to `11.5`.
  - `24.1` (checklist-approval) → author REQ-SPEC-016 as Req 3 criterion 4; repoint to `3.4`.
  - `24.2` (research-claim) → Class-B: author new Requirement 22 (REQ-SPEC-017) or delete task 39.16; repoint accordingly.
  - `25.1/25.2/25.3` (perf/a11y/UI) → author REQ-VERIFY-007/008 as Req 9 criteria 7/8; repoint `9.7, 9.8`.
  - `27.1/27.2/27.3` (audit-log) → author new Requirement 21 (REQ-AUDIT-001..003); repoint to `21.1/21.2/21.3`.

**P0-8 · Properties 25–30 referenced but not authored in design.md** [confidence: 7: F-PROP25/26/27/28/29/30-UNAUTH, F-DSGN-02, F-DSGN-03]
- **Evidence:** `design.md` properties stop at Property 24 (`:986`, file ends 990). `tasks.md` references Property 25 (`:715`), 26 (`:513,:716`), 27 (`:544,:717`), 28 (`:530`), 29 (`:721`); harness names Property 30 (`formal_verification_merged.py:483`). None authored in design.md.
- **Canonical:** Author Properties 25–30 (target = 30 properties).
- **Remediation:** Append after design.md:990 — P25 Amendment Monotonicity (CHECK-10a/10b, Validates 5.7), P26 Resumed-State Integrity (CHECK-11a/11b, Validates 11.5), P27 Checklist-Approval (CHECK-12a/12b, Validates 3.4), P28 Audit-Log Tamper Detection (Validates 21.1/21.2), P29 Research-Claim Labeling (Validates 22.1) [Class-B], P30 Omission-Declaration Gate (CHECK-13a/13b, Validates the REQ-SPEC-018 home). Use design.md's numbered `**Validates: Requirements N.M**` convention, not REQ-xxx codes.

**P0-9 · Tasks 32a/32b/32c (7 leaves) absent from dependency-graph waves** [confidence: 4: F-WAVE-32a/32b/32c, F-LOGIC-03]
- **Evidence:** Wave 24 = `["32.1"]` (tasks.md:865), wave 25 = `["33.1"]` (`:869`) — adjacent, no 32a/b/c between. Programmatic parse confirms 32a.1/32a.2/32b.1/32b.2/32b.3/32c.1/32c.2 absent from all 36 waves. Co-orphaned: 28.8, 28.9, 39.15, 39.16 (verified absent above).
- **Canonical:** All 11 orphan leaves scheduled.
- **Remediation:** Re-derive waves; insert all 11 leaves in dependency order between waves 24 and 25 (and wherever 28.8/28.9/39.15/39.16 belong); renumber or accept non-contiguous ids.

**P0-10 · design.md "five build phases" + Phase 4 "(optional)" + "six tables"** [confidence: 2: F-COUNT-07, F-DSGN-01]
- **Evidence:** `design.md:9` "five build phases"; `:13-17` table marks Phase 4 "(optional)"; `:138`/`:405` "all six tables"/"Six tables".
- **Canonical:** 5 required (0–4) + 2 optional (5–6); Phase 4 = PBT (required); tables → 8 if migrations kept (Class-B).
- **Remediation:** `design.md:9` → "five required build phases (0–4) plus two optional phases (5–6)"; `:17` relabel Phase 4 → "(PBT suite)", add Phase 5/6 rows; tables per Class-B decision.

### P1 — High (orphaned invariants, unbacked claims, logical gaps)

**P1-1 · CHECK-10/11/12/13 invariants have no requirement home** [confidence: 5: F-COV-01/02/03/04, F-REQ-01] — *resolved by the P0-7 authoring*: add REQ-COV-007 (Req 5.7, extend `:117`/`:379` range ..006→..007), REQ-STATE-005 (Req 11.5, extend `:212`/`:385` ..004→..005), REQ-SPEC-016 (Req 3.4, extend `:87`/`:394` ..015→..016), REQ-SPEC-018 (Class-B home — see below; harness label/req must match). Each new criterion carries an inline `*(Z3 CHECK-Na verified: ...)*` tag matching house style (requirements.md:126).

**P1-2 · REQ-LOOP-005 (HANDOFF-exits-0) unauthored** [confidence: 2: F-REQ-03, F-LOGIC-01 partner]
- **Evidence:** CHECK-3b/5b/5c/8c cite REQ-LOOP-005 (`formal_verification_merged.py:269,275,370`); `requirements.md` caps at REQ-LOOP-004 (`:260`/`:388`); 14.2 routes to HANDOFF but never states the Stop hook must exit-0.
- **Remediation:** Add Req 14 criterion 5 (REQ-LOOP-005), extend `:260` ..004→..005 and `:388`; add an "On HANDOFF" bullet to design.md (~`:750`) stating Stop exits 0, never 2, except the unproven-items gate.

**P1-3 · `failed` status unwritable** [confidence: 1: F-LOGIC-04] — enum admits `failed` (`design.md:355,424`; tasks.md:27) and Req 8.2 (`requirements.md:170`) + Property 23 (`design.md:980`) require the verifier to WRITE it, but the only permitted mutation is `unproven→proven` (`design.md:200,271,357,820`). **Class-B fix:** permit verifier-only `unproven→failed` (preferred — amend design.md:200/271/357/820 + add a Z3 check that `failed` never satisfies COMPLETE) OR drop `failed` from the enum and reword 8.2/Property 23.

**P1-4 · Spec-completion exit-code collision (Req 4.2 block vs Req 4.4 HANDOFF) with no tiebreak; gate unimplemented; phantom REQ-SPEC-021** [confidence: 2: F-LOGIC-05, F-LOGIC-06]
- **Evidence:** At pass cap with `violation_count>0`, Req 4.2 (`requirements.md:106`) mandates block, Req 4.4 (`:108`) mandates HANDOFF — no precedence stated. Reference `evaluate_stop` (`design.md:636-658`) never reads `violation_count` (no such column in run_state DDL `:457-468`), so the wiring-table claim (`design.md:196`) is unbacked. REQ-SPEC-021 appears only at `design.md:196`, never in requirements.md.
- **Remediation:** (a) Add precedence rule: "cap (Req 4.4) → HANDOFF supersedes the violation_count block (Req 4.2)" to requirements.md (after `:108`) and design.md (near `:196`, `:762`) — matches harness CHECK-3a/5b. (b) Add `violation_count INTEGER NOT NULL DEFAULT -1` to run_state DDL (`design.md:457-468`); add a "Check 0" to `evaluate_stop` reading it (ordered AFTER the cap/no-progress HANDOFF checks; also block on `<0` per design.md:736). **Do not** strike the violation_count clause — Req 4.2/design.md:736 bind it to the Stop hook. (c) Author REQ-SPEC-021 criterion in Req 4 (PRD range ..020..024 already exists at `:101`).

**P1-5 · No-progress pseudocode: undefined constants (NameError) + fires on 1 window instead of N=3** [confidence: 1: F-LOGIC-07]
- **Evidence:** `N_PROGRESS_WINDOW` (`design.md:617,623,650`) and `MAX_TURNS_PER_SLICE` (`:653,655`) are never defined/imported → NameError. `:633 return no_progress` returns a single-window boolean; `:612 window = no_progress_n` is dead. Contradicts requirements.md:264 / Property 8 (design.md:862) "N=3 consecutive".
- **Remediation:** Define both constants before `:607` (=3, =25); change `:633` to `return run_state.no_progress_n >= N_PROGRESS_WINDOW`; change lookback windows (`:615-624`) to `slices_back=1`; remove dead local `:612`.

**P1-6 · EARS glossary lists 6 patterns; everywhere else uses 5** [confidence: 1: F-LOGIC-08] — `requirements.md:31` lists "Unwanted behaviour, Optional, Complex" but Req 1.4 (`:65`), schema enum (`design.md:330`), SMT table (`:495-501`), Property 16 (`:924`), encoder (`tasks.md:65`) all use 5 and exclude "Complex". **Fix:** `requirements.md:31` drop "Complex", normalize "Unwanted behaviour"→"Unwanted".

**P1-7 · Property 24 (implementer-cannot-self-verify) unbacked by data model** [confidence: 1: F-LOGIC-09] — `evidence_records` (`design.md:442-454`) has no actor column; field name split (`acting_agent` at tasks.md:705 vs `actor_agent` at tasks.md:454/519). **Fix:** add `actor_agent TEXT NOT NULL` + CHECK constraint to evidence_records; rename `acting_agent`→`actor_agent` at tasks.md:705 only (454/519 already correct); document whether it's a row column or a 5th artifact field (the 4-field EvidenceRecord schema is `additionalProperties:false`).

**P1-8 · Cost/token budget has no numeric DEFAULT; retry budget unmodeled** [confidence: 1: F-LOGIC-10] — every sibling bound has a number (requirements.md:351) but the cost/token budget has none (requirements.md:264, design.md:745, Property 9 design.md:868); retry budget (Req 14.3, DEFAULT=3) has no `retry_count` column and no enforcer. **Fix:** add a numeric budget default (or mandate operator-set) at requirements.md:351; add `retry_count` to run_state DDL + migration 28.5 + Check 4/5 in stop_hook task 5.1; trace 14.3.

**P1-9 · "in-scope" gate predicate is undefined** [confidence: 1: F-LOGIC-11] — used at requirements.md:21/23/34/125/200, design.md:196/836 but no `in_scope` field exists in CoverageItem schema (`design.md:307,309-362`) or coverage_items table (`:421-428`); `evaluate_stop` filters on status only (`:641`). **Fix:** declare all feature_list.json items in-scope by construction and drop the "in-scope" qualifier (matches the reference code) OR add an explicit `in_scope` boolean and filter on it. Pick one, apply uniformly.

**P1-10 · Sandbox security boundary (Req 17.4) conflated with git worktrees; no design/tech/task** [confidence: 1: F-LOGIC-12] — Req 17.4 (`requirements.md:310`) requires an isolated sandbox; "sandbox" appears nowhere else; no isolation tech chosen; Req 17.4 has no task and no design traceability. **Fix:** add a Sandbox/Untrusted-Code Isolation section to design.md choosing a concrete tech (container+seccomp / gVisor / Firecracker), add a `sandbox_runner` component (design.md:122-142), add a task with `_Requirements: 17.4`, and annotate worktrees (design.md:198/226/235/590/852) as a collision boundary only — NOT the security sandbox.

**P1-11 · Criterion 10.5 (ambiguous→blocked) unmodeled; gate is "block iff unproven" not "block iff not-proven"** [confidence: 1: F-LOGIC-13] — Req 10.5 (`requirements.md:204`) requires ambiguous→blocked, but harness gate is total boolean `gateBlock==unproven` (`formal_verification_merged.py:139`) and the rule is literally "block iff unproven" (design.md:836), so an in-enum `failed` status (and out-of-enum/missing values) escapes the block. **Fix:** restate gate as "any status not EXACTLY 'proven' is treated as unproven for gating" (design.md:196/836); add a Z3 assertion generalizing the existing amendment_axioms pattern (`:419`); add an Error-Handling row for malformed feature_list.json.

**P1-12 · Audit-log producer/trigger absent from design + requirement anchor missing** [confidence: 2: F-LOGIC-03, F-DANGLE-27] — `gate_audit_log` has a table (tasks.md:453) and verifier (32b) but no design-level producer; the only wiring instruction (tasks.md:521 "wire into all five hooks") is in an unscheduled orphan task and says "five" not "six". **Fix:** add `gate_audit_log` CREATE TABLE to design.md (+ a Hook Wiring producer row), fold `append_gate_decision()` into hook tasks 5.1/6.1/8.1 (or make 32b a hard predecessor), schedule the leaves (P0-9), author REQ-AUDIT (P0-7).

**P1-13 · Audit count drift 32 vs live 34** [confidence: 1: F-COUNT-01(audit)] — `findings.md` describes a "hardcoded TOTAL=29 / 32 actual" bug that does NOT exist on disk (the file self-counts; CHECK-13a/13b added since). **Fix:** strike findings.md N-1/N-2; set all audit counts to 34.

### P2 — Medium (hygiene, internal contradictions)

- **P2-1 · Property count "29" vs "24" in tasks.md** (F-COUNT-05, F-PROP-CONTRA-2429): `tasks.md:619` "all 29" vs `:744`/`:758` "all 24". Canonical (after P0-8 authoring) = **30**; if Properties 25–30 are authored, set all three to 30; else 24. Recommended: author them → 30.
- **P2-2 · "five hooks" → "six"** (F-COUNT-06): `tasks.md:521` and `:589`.
- **P2-3 · "8 migrations (001-008)" vs design "six tables"** (F-COUNT-11): tasks.md:459/551. Resolve with the tables Class-B decision (8 recommended → author the 2 CREATE TABLE blocks).
- **P2-4 · 39.15/39.16 absent from waves** (F-WAVE-39SUBSET): fold into P0-9 wave regeneration.
- **P2-5 · Requirements 8/11/15/20 have tasks but no design property** (F-REQ-NO-PROP-WIRING): add properties or annotate "architecture/config — no property invariant".
- **P2-6 · design.md:778 "all 21 PRD checks"** (F-DSGN-05): →"all 34 harness checks" (covered by P0-1).
- **P2-7 · findings.md mis-locates tasks.md content** (F-PHANTOM-03): re-derive citations (covered by P0-4).
- **P2-8 · Superseded PRDs assert "21/21" as headline** (F-COUNT-04): add a deprecation banner to both byte-identical superseded PRDs pointing to README + merged harness; annotate the three 21/21 occurrences (`:5,:289,:312`) inline as a known hardcoding artifact (the archived harness ran 23 checks, hardcoded 21). **Do NOT** preserve 21/21 as "historically accurate" and **do NOT** rewrite to 34.

### P3 — Scope decisions (deferral hygiene)

- **P3-1 · Omission-declaration gate half-adopted** (F-SCOPE-01): harness-proven (CHECK-13/REQ-SPEC-018/Property 30) but absent from all three spec docs. **Recommend IN for v1** — the oracle already made the call; back-propagate (covered by P0-7/P0-8). This is the strongest research-aligned candidate.
- **P3-2..06 · Net-new candidates** (F-SCOPE-02..06): eval-gating-in-CI (OUT, defer Phase 4), Pact/CDC (OUT, Phase 1 conditional on multi-service), runtime structured-output enforcement (OUT, Phase 1), DAST/OWASP ZAP + native `/security-review` (split: `/security-review` IN cheap, DAST OUT Phase 1), progressive delivery/feature-flags (OUT, Phase 4).
- **P3-7 · Out-of-scope section stale** (F-SCOPE-07): `requirements.md:11` lists only 4 exclusions, no deferred-with-rationale list. **Fix:** append a "Deferred with rationale (Phase 1+)" subsection capturing F-SCOPE-02..06; reconcile requirements.md:11's "performance/load testing layer OUT" against the new REQ-VERIFY-007 (perf/a11y), and amend Req 9.1's "four layers" to admit a 5th NFR layer (F-DANGLE-REQVERIFY).
- **P3-8 · Audit/state layer under-built** (F-SCOPE-08): cross-ref flag; surface REQ-AUDIT/REQ-STATE-005/REQ-COV-007 into requirements.md (covered by P0-7); note immudb/Hyperledger as Phase-2+ deferrals.

---

## 4. Remediation Map (ordered execution plan)

**Class-A = mechanical reconciliation** (string/number fixes with one correct value). **Class-B = design decisions** requiring an explicit choice (recommended default in **bold**). Execute Class-A batches first (they unblock verification), then Class-B authoring, then re-derive the wave graph last (depends on all task additions).

### Class-B decisions to confirm BEFORE authoring (4 decisions)

| # | Decision | Options | **Recommended default** |
|---|---|---|---|
| B1 | Postgres tables 6 or 8? | Drop migrations 007/008, or author 2 CREATE TABLE blocks | **8** — author `requirement_versions` + `gate_audit_log` in design.md; the audit-log feature (REQ-AUDIT, Property 28) depends on it |
| B2 | `failed` status writable? | Allow `unproven→failed` transition, or drop `failed` from enum | **Allow the transition** — Req 8.2 + Property 23 already require the verifier to write it |
| B3 | REQ-SPEC-018 (omission gate) home + research-claim (REQ-SPEC-017) | Home under existing req vs new heading; keep vs delete task 39.16 | **Keep both; new Requirement 22 for research-claim (REQ-SPEC-017); REQ-SPEC-018 as a Req 9 criterion** (harness label must match the chosen ID) |
| B4 | Add CHECK-14 family for audit-log tamper (Property 28)? | PBT-only, or add Z3 check | **PBT-only for v1** — keep harness at 34; Property 28/29 are PBT properties without a Z3 oracle (note this explicitly so the count stays honest) |

### Batch 1 — Class-A count/filename reconciliation (no dependencies)

| File | Edits |
|---|---|
| `requirements.md` | `:9` 21/21→34/34; `:358` `formal_verification.py`→`verification/formal_verification_merged.py` + 21/21→34/34; `:31` drop "Complex", "Unwanted behaviour"→"Unwanted" |
| `design.md` | `:547` filename + "21 such checks"→"34 such checks (14 core + 12 Kiro + 8 new)"; `:588` filename + "all 21 checks pass"→"all 34 checks pass"; `:778` "21 PRD checks"→"34 harness checks"; `:9` "five build phases"→"five required build phases (0–4) plus two optional (5–6)"; `:17` Phase 4 "(optional)"→"(PBT suite)" + add Phase 5/6 rows |
| `tasks.md` | `:91/:258/:301` 29→34; `:521/:589` "five hooks"→"six hooks" |
| `docs/superseded/*PRD*.md` (both) | add deprecation banner; annotate `:5/:289/:312` "21/21" as superseded hardcoding artifact |

**Verify after Batch 1:**
```
grep -rn '21/21\|29/29' .kiro/specs/ README.md          # → 0 hits
grep -rn 'all 29 checks\|all 21 checks' .kiro/specs/     # → 0 hits
grep -rn 'formal_verification\.py' .kiro/specs/          # → 0 hits (only merged)
grep -n 'five build phases' .kiro/specs/spec-to-evidence-control/design.md  # → 0
grep -n 'five hooks' .kiro/specs/spec-to-evidence-control/tasks.md          # → 0
```

### Batch 2 — Class-A logical-defect code fixes in design.md (the load-bearing bug fixes)

| File:line | Edit |
|---|---|
| `design.md:649-650`, `:655-656` | `return block(...)` → `return allow()` (HANDOFF exit-0; **P0-5**) |
| `design.md` before `:607` | define `N_PROGRESS_WINDOW = 3`, `MAX_TURNS_PER_SLICE = 25` (**P1-5**) |
| `design.md:633` | `return no_progress` → `return run_state.no_progress_n >= N_PROGRESS_WINDOW`; `:615-624` lookback `slices_back=1`; remove dead `:612` |
| `design.md:200/271/357/820` | per B2: permit verifier `unproven→failed` (**P1-3**) |
| `design.md:196/836` | gate restated "not EXACTLY proven → treated as unproven" (**P1-11**); add precedence rule cap→HANDOFF supersedes block (**P1-4**) |
| `design.md:457-468` | add `violation_count INTEGER NOT NULL DEFAULT -1`, `retry_count INTEGER NOT NULL DEFAULT 0` (**P1-4, P1-8**) |
| `design.md:636-658` | add Check 0 reading `violation_count` (after cap/no-progress checks) |
| `design.md:442-454` | add `actor_agent TEXT NOT NULL` + CHECK (**P1-7**) |
| `design.md` ~`:750`, `:122-142`, `:203` | HANDOFF-exits-0 bullet; sandbox component + section (**P1-10**); PreToolUse resume-integrity row (**P0-6**) |

**Verify after Batch 2:**
```
grep -n 'return block' .kiro/specs/spec-to-evidence-control/design.md   # only the unproven branch (~642-644)
grep -nE 'N_PROGRESS_WINDOW *=|MAX_TURNS_PER_SLICE *=' .kiro/specs/spec-to-evidence-control/design.md  # → 2 defs
python3 verification/formal_verification_merged.py   # still 34/34, exit 0 (harness unchanged)
```

### Batch 3 — Class-B authoring: requirements.md (after B1–B4 confirmed)

Add, in `requirements.md`:
- Req 3 criterion 4 = REQ-SPEC-016 (checklist-approval); extend `:87`/`:394` ..015→..016
- Req 5 criterion 7 = REQ-COV-007 (amendment monotonicity); extend `:117`/`:379` ..006→..007
- Req 9 criteria 7/8 = REQ-VERIFY-007/008 (perf-a11y / UI-completeness) + REQ-SPEC-018 home (omission gate); extend `:179`/`:383` ..006→..008; amend Req 9.1 "four layers"→admit NFR layer
- Req 11 criterion 5 = REQ-STATE-005 (resumed-state integrity); extend `:212`/`:385` ..004→..005
- Req 14 criterion 5 = REQ-LOOP-005 (HANDOFF-exits-0); extend `:260`/`:388` ..004→..005
- Req 4: author REQ-SPEC-021 criterion (precedence)
- **New Requirement 21** = Audit-Log Tamper Detection (REQ-AUDIT-001..003)
- **New Requirement 22** = Research-Claim Authority Labeling (REQ-SPEC-017) [B3]
- Update Critical Invariants list (`:356-367`): repoint harness/count, append invariants 8–12 (CHECK-10a/11a/12a/13a/5b)
- `:11` add "Deferred with rationale (Phase 1+)" subsection (P3-7)

**Verify after Batch 3:**
```
grep -c '^### Requirement' .kiro/specs/spec-to-evidence-control/requirements.md   # → 22
grep -nE 'REQ-COV-007|REQ-STATE-005|REQ-SPEC-016|REQ-AUDIT-001|REQ-VERIFY-007|REQ-LOOP-005' \
  .kiro/specs/spec-to-evidence-control/requirements.md   # → all present
```

### Batch 4 — Class-B authoring: design.md Properties 25–30 + tables (B1)

- Append Properties 25–30 after `design.md:990` (P0-8), each with `**Validates: Requirements N.M**` and Z3 check label
- Per B1: add `requirement_versions` + `gate_audit_log` CREATE TABLE after `:482`; flip `:138`/`:405` "six/Six"→"eight/Eight"; add audit-log producer Hook Wiring row
- Add design properties or "no-property" annotations for Req 8/11/15/20 (P2-5)

**Verify after Batch 4:**
```
grep -cE '^### Property [0-9]+' .kiro/specs/spec-to-evidence-control/design.md   # → 30
grep -ciE 'CREATE TABLE' .kiro/specs/spec-to-evidence-control/design.md          # → 8 (if B1=8)
grep -n 'six tables\|Six tables' .kiro/specs/spec-to-evidence-control/design.md  # → 0
```

### Batch 5 — Class-A: tasks.md token repointing + property count

- Repoint all dangling `_Requirements:_`/`Validates:` tokens per P0-7 table (21.1→drop; 22.1→5.7; 23.1→11.5; 24.1→3.4; 24.2→22.1; 25.x→9.7/9.8; 27.x→21.1/21.2/21.3)
- `:619` "all 29 correctness properties"→"all 30" (per B4/P2-1); `:459/:551` "8 migrations"→keep 8 (B1)
- Rename `acting_agent`→`actor_agent` at `:705` (P1-7)
- Relocate state_integrity wiring (`:508`) to pre_tool_use_hook (P0-6)

**Verify after Batch 5:**
```
# no _Requirements:/Validates: token > 22 and no 23/24/25/27 dangles
grep -nE '(Requirements?|Validates):.*\b(2[3-9]|3[0-9])\.[0-9]' \
  .kiro/specs/spec-to-evidence-control/tasks.md   # → 0
grep -n 'acting_agent' .kiro/specs/spec-to-evidence-control/tasks.md  # → 0
```

### Batch 6 — Class-A: regenerate the wave graph (LAST — depends on all task additions)

- Re-derive `tasks.md:765-912` waves so every body-defined leaf appears exactly once; insert the 11 orphans (28.8, 28.9, 32a.1, 32a.2, 32b.1, 32b.2, 32b.3, 32c.1, 32c.2, 39.15, 39.16) in dependency order; renumber wave ids.

**Verify after Batch 6:**
```
python3 - <<'PY'
import json,re,io
src=open(".kiro/specs/spec-to-evidence-control/tasks.md").read()
m=re.search(r'```json\s*(\{.*?"waves".*?\})\s*```', src, re.S)
waves=json.loads(m.group(1))["waves"]
flat={t for w in waves for t in w["tasks"]}
need={"28.8","28.9","32a.1","32a.2","32b.1","32b.2","32b.3","32c.1","32c.2","39.15","39.16"}
print("MISSING:", need-flat or "none")
PY
```

### Batch 7 — Audit-artifact remediation

- `reconciliation-report.md`: re-title "INTENDED — NOT YET APPLIED"; 32/32→34/34 (`:8,:16,:29`); strip `PRD_MERGED` (`:10`); correct rows 18/20/22/24 to live values (or mark as targets)
- `findings.md` + `audit-plan.md`: regenerate against live files; delete beyond-EOF citations (design.md:1009/1025/1044/1048/1052, requirements.md:400) and all `PRD_MERGED:N`; counts→34
- `audit-plan.md:3`: reconcile "No fixes applied" wording with the partial fixes on disk

**Verify after Batch 7:**
```
grep -rn 'PRD_MERGED' audit/                                  # → 0
grep -rnE 'design\.md:(99[1-9]|1[0-9]{3})|requirements\.md:(39[5-9]|[4-9][0-9]{2})' audit/   # → 0 (no beyond-EOF)
grep -rn '32/32\|28 requirement\|45 wave\|eight tables' audit/  # → only inside an explicit "TARGET/INTENDED" context
```

---

## 5. Residual-Drift Checklist

After all batches, **every command below must return ZERO stale hits** (run from repo root `/Users/danielmanzela/Agentic-Driven SDLC Platform`):

```bash
# 1. Stale Z3 counts gone from live spec + README
grep -rn '21/21\|29/29\|32/32' .kiro/specs/ README.md
grep -rn 'all 29 checks\|all 21 checks\|all 29 formal' .kiro/specs/

# 2. Deprecated harness filename only in superseded/audit/plans contexts
grep -rn 'formal_verification\.py' .kiro/specs/ README.md     # → 0
grep -rln 'formal_verification\.py' . | grep -v 'superseded\|audit/\|docs/plans\|_merged'   # → 0

# 3. Phase / hooks / EARS wording
grep -rn 'five build phases\|Phase 4 (optional)' .kiro/specs/spec-to-evidence-control/design.md
grep -rn 'five hooks\|all five hooks' .kiro/specs/spec-to-evidence-control/tasks.md
grep -n 'Complex\|Unwanted behaviour' .kiro/specs/spec-to-evidence-control/requirements.md

# 4. Tables wording matches chosen count (B1=8)
grep -n 'six tables\|Six tables' .kiro/specs/spec-to-evidence-control/design.md   # → 0 if B1=8

# 5. No dangling requirement citations (nothing above Requirement 22)
grep -nE '(Requirements?|Validates):[^A-Za-z]*\b(2[3-9]|[3-9][0-9])\.[0-9]' \
  .kiro/specs/spec-to-evidence-control/tasks.md          # → 0
# every new harness REQ-ID now has a home
for id in REQ-COV-007 REQ-STATE-005 REQ-SPEC-016 REQ-SPEC-018 REQ-AUDIT-001 REQ-VERIFY-007 REQ-VERIFY-008 REQ-LOOP-005; do
  grep -q "$id" .kiro/specs/spec-to-evidence-control/requirements.md || echo "ORPHAN: $id"
done                                                       # → no ORPHAN lines

# 6. Heading / property / table counts hit canonical targets
test $(grep -c '^### Requirement' .kiro/specs/spec-to-evidence-control/requirements.md) -eq 22  || echo "REQ count != 22"
test $(grep -cE '^### Property [0-9]+' .kiro/specs/spec-to-evidence-control/design.md) -eq 30   || echo "PROP count != 30"

# 7. All 11 orphan leaves scheduled in waves (parser from Batch 6) → MISSING: none

# 8. Infinite-block defect gone: HANDOFF branches allow(), only unproven blocks
grep -n 'return block' .kiro/specs/spec-to-evidence-control/design.md   # only ~1 hit, the unproven-items branch

# 9. No phantom audit citations
grep -rn 'PRD_MERGED' audit/ .kiro/                        # → 0
grep -rnE 'design\.md:(99[1-9]|1[0-9]{3})|requirements\.md:(39[5-9]|[4-9][0-9]{2})' audit/   # → 0

# 10. Oracle still green and self-counts 34 (must be the LAST gate)
python3 verification/formal_verification_merged.py | tail -3   # → "Result: 34/34 checks passed", exit 0
```

**Final acceptance gate:** the harness run (item 10) must print `34/34` exit 0 — it is the authoritative oracle and must remain untouched by all edits above (no edit in any batch modifies `verification/formal_verification_merged.py`, except the optional B4 CHECK-14 family, which is deferred). If any check 1–9 returns a hit, that file has residual drift and the remediation is incomplete.

---

**Key deliverable files (absolute paths):**
- Oracle (do not edit): `/Users/danielmanzela/Agentic-Driven SDLC Platform/verification/formal_verification_merged.py`
- Already-synced reference: `/Users/danielmanzela/Agentic-Driven SDLC Platform/README.md`
- Edit targets: `/Users/danielmanzela/Agentic-Driven SDLC Platform/.kiro/specs/spec-to-evidence-control/{requirements.md, design.md, tasks.md}`
- Audit artifacts to retract/regenerate: `/Users/danielmanzela/Agentic-Driven SDLC Platform/audit/{reconciliation-report.md, findings.md, audit-plan.md}`
- Superseded (banner only): `/Users/danielmanzela/Agentic-Driven SDLC Platform/docs/superseded/*PRD*.md`