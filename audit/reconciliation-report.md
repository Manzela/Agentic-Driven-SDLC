# Reconciliation Report — Spec-to-Evidence Control System

**Date:** 2026-06-15
**Status:** ✅ **APPLIED.** The cross-document drift catalogued in [`audit/verification-report.md`](verification-report.md) has been remediated in place and verified. This document records what was changed and the verification evidence.
**Authoritative analysis:** [`audit/verification-report.md`](verification-report.md) (57 confirmed findings, 0 refuted, from a 65-agent parallel audit).

> **Supersedes** the earlier version of this file, which asserted a reconciled state ("32/32, 28 requirements, 8 tables, 45 waves") that was **false on disk** and contradicted `audit-plan.md`'s "no fixes applied". Those numbers were never correct; the true applied values are below. The harness (self-counting, 34) is the authoritative oracle and was confirmed by execution.

## Update — 2026-06-15 (P3 Market-Research addendum + meta-analysis reconciliation pass)

After this report's original verification-audit reconciliation (to 22 requirements), the specification was expanded by a Merge-Reconciliation and P3 Market-Research addendum to **32 requirements** (Reqs 21–32: HANDOFF semantics, amendment versioning, resumed-state integrity, checklist/research integrity, perf/a11y/UI-completeness, reasoning-loop detection, tamper-evident audit log, role taxonomy, structured omission declaration, eval-gating, DAST baseline, kill-switch), **49 dependency-graph waves**, and **57 tasks**. A subsequent meta-analysis pass (`audit/meta-analysis-harness-and-audit-trail.md`) re-applied two fixes the addendum edit had regressed — the infinite-block HANDOFF ordering in `design.md` `evaluate_stop` (HANDOFF triggers now evaluated before the unproven-items gate, matching Z3 CHECK-5b/5c/8c), and a `design.md` + `PRD_MERGED` 32→34 check-count typo. The canonical table below now reflects the current 32-requirement state.

## Canonical values — current state (re-verified 2026-06-15)

| Metric | Value | Verification command → result |
|---|---|---|
| Z3 assertions | **34** | `python3 verification/formal_verification_merged.py` → `Result: 34/34 checks passed`, exit 0 (self-counted, `TOTAL = checks_run`) |
| Requirements (`### Requirement`) | **32** | `grep -c '^### Requirement' requirements.md` → 32 (20 original + Reqs 21–29 Merge-Reconciliation + Reqs 30–32 P3 Market-Research) |
| Correctness properties (`### Property`) | **30** | `grep -cE '^### Property [0-9]+' design.md` → 30 (24 + Properties 25–30) |
| Postgres tables / migrations | **8 / 001–008** | `grep -c 'CREATE TABLE' design.md` → 8 (added `requirement_versions`, `gate_audit_log`) |
| Dependency-graph waves | **49 (0–48)** | `grep -cE '"id":' tasks.md` → 49; JSON parses; all leaf tasks scheduled |
| Top-level tasks (`- [ ] N.`) | **57** | `grep -cE '^- \[ \] [0-9]+\.' tasks.md` → 57 |
| Phases | **5 required (0–4) + 2 optional (5–6)** | no live "five build phases"/"Phase 4 (optional)" |
| Hooks | **6** | no live "five hooks" |
| EARS patterns | **6** (5 base + Complex composition) | live glossary (requirements.md:31) lists 6 — Ubiquitous, Event-driven, State-driven, Unwanted behaviour, Optional, Complex; the `ears_pattern` enum and validator operate over the 5 base patterns, with Complex documented as a composition (design.md:1188). "Complex" was NOT removed — the longer 6-pattern glossary is canonical. |
| Harness filename | `verification/formal_verification_merged.py` | no live `formal_verification.py` outside `docs/superseded/` |

## What was applied (7 batches; see verification-report.md §4 for the full map)

1. **Count/filename/phase/EARS reconciliation** — 21/21 & 29/29 → 34/34; old harness filename repointed; phase model unified to 5+2. *(EARS: the live glossary keeps the longer 6-pattern list — 5 base + Complex composition; the operative `ears_pattern` enum uses the 5 base patterns. The earlier "drop Complex → 5" recommendation was NOT adopted; 6 is canonical.)*
2. **Logical-defect fixes (design.md)** — the **infinite-block defect** fixed (HANDOFF paths now `allow()`/exit-0, matching Z3 CHECK-5b/5c/8c); `evaluate_stop` precedence corrected; no-progress constants defined and N=3 streak fixed; `failed` status made writable; fail-closed "not-exactly-proven → block".
3. **requirements.md authoring** — REQ-COV-007, REQ-STATE-005, REQ-SPEC-016, REQ-SPEC-018, REQ-VERIFY-007/008, REQ-LOOP-005, REQ-SPEC-021 as criteria; new Requirements 21 (REQ-AUDIT) & 22 (REQ-SPEC-017); invariants 8–12 added; threshold registry completed (token budget, K, N).
4. **design.md authoring** — Properties 25–30; tables 007/008 + full hash-chain spec; resume-integrity & checklist-approval PreToolUse rows; `actor_agent` column; 5th verifier layer; sandbox isolation section.
5. **tasks.md repointing** — all dangling requirement citations (21.1/22.1/23.1/24.1/24.2/25.x/27.x) repointed to real homes; property count → 30; omission-gate (Property 30) wired; `acting_agent`→`actor_agent`; resume-integrity relocated to PreToolUse; new task 24a (gitleaks).
6. **Wave-graph regeneration** — 12 orphan leaves scheduled; 36 → 39 waves; validated 100% coverage. *(Later expanded to 49 waves by the P3 addendum — see the Update note above.)*
7. **Audit-trail correction** — this report rewritten; `findings.md` and `audit-plan.md` banner-superseded; superseded PRDs banner-noted.

## Class-B design decisions adopted (override-able)

| # | Decision | Adopted |
|---|---|---|
| B1 | Postgres tables 6 or 8 | **8** — authored `requirement_versions` + `gate_audit_log` |
| B2 | `failed` status writable | **Yes** — verifier-only `unproven→failed` / `failed→unproven` |
| B3 | Omission-gate (REQ-SPEC-018) + research-claim (REQ-SPEC-017) homes | REQ-SPEC-018 → Req 9.9; REQ-SPEC-017 → new Req 22 |
| B4 | CHECK-14 for audit-log tamper | **No** — harness stays 34; Properties 28/29 are PBT-only (noted explicitly) |

These match the prior owner intent documented in the earlier reconciliation draft; change any and re-run the residual-drift checklist (verification-report.md §5).

## Remaining (scope decisions, not drift)

The P3 market-research capabilities are net-new scope, deferred-with-rationale in `requirements.md` (eval-gating-in-CI, Pact/CDC, runtime structured-output enforcement, DAST, progressive delivery). The omission-declaration mechanism (research's #1 failure mode) **was adopted** (REQ-SPEC-018 / Property 30 / CHECK-13). The `/security-review` pass is adopted; full DAST deferred. One latent design detail — the REASONING-span representation (REQ-OBS-006) — is noted but not yet authored; it is not cited anywhere, so it creates no dangling reference.

## Verification method

Static enumeration + JSON parse + **harness execution** (z3 4.16.0 installed locally; `34/34`, exit 0 confirmed by running, not inferred). All 10 residual-drift gates in verification-report.md §5 return zero stale hits.
