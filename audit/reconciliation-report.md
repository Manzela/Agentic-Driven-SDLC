# Reconciliation Report — Spec-to-Evidence Control System

**Date:** 2026-06-15
**Companion to:** `audit/findings.md`, `audit/audit-plan.md`
**Action:** the audited gaps were fixed and the five canonical artifacts were back-propagated into alignment. This documents what changed and the verification evidence.

## Files changed
- `formal_verification_merged.py` — count bug fixed (self-counts; 32/32).
- `formal_verification.py` — deprecation banner (superseded; do not run/cite).
- `requirements.md`, `design.md`, `tasks.md`, `PRD_MERGED_canonical_spec_to_evidence.md` — reconciled to the canonical values + Class-B decisions.
- *(Untouched: the two pre-merge PRD copies in the primary dir — `Kiro's Updated PRD…md`, `PRD_spec_to_evidence…md` — are superseded inputs, not part of the canonical set.)*

## Canonical values now consistent across ALL files (verified)
| Metric | Value | Verification |
|---|---|---|
| Z3 assertions | **32** (self-counted) | `grep -c '^check(' = 32`; `TOTAL = checks_run`; `py_compile` OK; all 4 docs say "32/32"; no live "29/29" |
| Correctness properties | **29** | Properties 25–29 authored in design.md (5 headings); task 39 = "all 29"; kept distinct from the 32 Z3 count |
| Requirements | **28** | 28 `### Requirement` headings; PRD says "28 (20+8)" |
| Tasks | **53** | tasks 43–53 present (11); PRD says "53" |
| Dependency-graph waves | **45 (0–44)** | JSON parses; tasks 43–53 + subtasks all scheduled |
| Phases | **5 required (0–4) + 2 optional (5–6)** | no live "five phases"/"4-phase" anywhere |
| Postgres tables / migrations | **8 / 001–008** | 8 `CREATE TABLE`; inventory rows for 007/008; tasks 28.7/28.8; no live "six tables" |
| Hooks | **6** | hook-wiring table 11 rows; no live "five hooks" |
| Old harness refs | **deprecation-only** | no live "formal_verification.py / 21 checks" outside deprecation context |

## Class-B design decisions applied (override-able — each marked `*(Reconciliation 2026-06-15: …)*` in-doc)
| Gap | Decision implemented |
|---|---|
| N-1/N-2 harness count | `check()` increments `checks_run`; `TOTAL = checks_run`; reports true 32; old harness banner-deprecated |
| N-4 REQ-STATE-005 enforcement | SessionStart computes `resume_integrity_ok`; new **PreToolUse integrity guard** blocks first write on mismatch (hook-wiring row + run_state column + task 49.1) |
| N-5 audit-log producer | `tools/audit_log.append()` called by Stop/PreToolUse/SubagentStop; `audit_verify.py` verifies (tasks 52.1–52.3) |
| N-6 hash chain | genesis `sha256("")` sentinel, canonical-JSON form, `entry_hash` includes `seq`+`created_at`, verified at merge (CI) + on-demand |
| N-7 in-scope as data | `in_scope` boolean on CoverageItem schema + `coverage_items`; gates count only in-scope items |
| N-8 `failed` status | `unproven→failed`, `failed→unproven` allowed; only `*→proven` needs full evidence (status guard + schema + Property 3) |
| N-9 exit-code collision | lex specialis: HANDOFF (exit 0) wins at `SPEC_COMPLETION_HARD_CAP=7`; exit-2 only before the cap |
| N-11 sandbox | devcontainer (local) / E2B (CI), egress-denied, worktree mounted into the sandbox; design subsection added |
| N-12/N-24/N-27 defaults | token budget 1,000,000/slice, reasoning-loop K=3, retry budget 3/slice + `run_state.retry_count` |
| K18/N-21 verifier | 5th layer (k6/Lighthouse + axe-core) in verifier def + Req 9.1 + `perf_a11y_verifier` component |
| K19 REASONING span | custom attribute `claude.span.kind="reasoning"` on an INTERNAL span (not a new SpanKind) |
| K12 coverage tool | pytest-cov / coverage.json named as the per-touched-file generator |
| K17 secrets tool | gitleaks (workflow component + required CI status check) |

## What remains — a scope decision, NOT a reconciliation gap (deliberately not auto-applied)
The **P3 market-research capabilities** are net-new scope, not internal inconsistencies. They were *not* unilaterally added to v1 (doing so would substantially change product scope). Decide in/out:
1. **Edge-case "flag-the-omission" mechanism** — the research's #1 named failure mode; the spec requires coverage (UNMAPPED gate) but has no "agent must declare what it left out" signal. *(Strongest candidate to add.)*
2. Eval-gating-in-CI (Langfuse/Phoenix don't gate) · 3. Consumer-driven contract testing (Pact) · 4. Runtime structured-output schema enforcement (Pydantic/BAML) · 5. DAST / OWASP ZAP · 6. Progressive-delivery / feature-flag kill-switch.

**Recommended:** add #1 as a requirement; add #2–#6 to the explicit *deferred-with-rationale* out-of-scope list (the spec's own "no pain point silently unaddressed" discipline) unless you want them in v1.

## Verification method
Static enumeration + JSON parse + `py_compile` (Z3 not installed locally, so the harness's runtime "32/32" print is inferred from the now-self-counting logic, not executed here — CI installs `z3-solver` and will print the true count).
