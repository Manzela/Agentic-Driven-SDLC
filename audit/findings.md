# Spec-to-Evidence Control System — Forensic Audit Findings

> ⚠️ **SUPERSEDED (2026-06-15) by [`audit/verification-report.md`](verification-report.md).** This earlier audit was performed against a larger "canonical merged" copy (`PRD_MERGED_canonical_spec_to_evidence.md`) that **does not exist** in this repository; many of its line citations point beyond the actual file EOFs and its harness count (32/29) undercounts the live self-counting harness (**34**). It is retained for provenance only. For the authoritative, applied analysis against the live files, see `verification-report.md` and `reconciliation-report.md`. *(Update 2026-06-15: the `PRD_MERGED_canonical_spec_to_evidence.md` file this audit flagged as nonexistent was subsequently materialized into `.kiro/specs/spec-to-evidence-control/`, and the spec was expanded to **32 requirements**. The current-state analysis and final reconciliation are in `meta-analysis-harness-and-audit-trail.md`.)*


**Date:** 2026-06-15
**Auditor:** independent cross-document forensic pass (Claude) + 37-agent verification workflow (2.77M tokens), cross-checked against direct file reads.
**Scope:** `requirements.md`, `design.md`, `tasks.md`, `PRD_MERGED_canonical_spec_to_evidence.md`, `formal_verification_merged.py`, `formal_verification.py`, against `Agentic-Driven SDLC.md` (reference architecture) and `AI_SDLC_Market_Research.pdf`.
**Method:** every claim verified against the *current* file contents; each new gap was put through an adversarial skeptic that tried to refute it. Kiro's 19 findings were re-verified, not assumed.

---

## 0. Headline / meta-finding

**The documents are NOT fully synced.** Kiro's audited gaps were closed by *appending* a "Merge Reconciliation Addendum" to each file (and by writing a new 29-check harness), but **the addenda were never back-propagated into the canonical tables, graphs, subagent definitions, and count statements they supersede.** The result is a document set that is internally bifurcated: a *normative core* (component inventory, dependency graph, property catalogue, hook-wiring table, phase prose, count claims) that still reflects the pre-merge state, and a *prose appendix* that describes the post-merge state. Wherever a downstream artifact (CI smoke test, wave scheduler, PBT suite, migration runner) consumes the normative core, the merge deltas are invisible to it.

**Verdict on Kiro's analysis:** materially **stale but directionally right**. Kiro audited an earlier snapshot (the superseded `formal_verification.py`, pre-addendum docs). Of Kiro's 19 findings: **1 fully resolved** (K1), **7 still confirmed**, **11 partially addressed** (real residual remains). None were pure false positives. But Kiro **missed the single most important defect** — see Finding N-1.

---

## 1. The harness count is wrong — in BOTH harnesses (NEW — highest priority)

### N-1 🔴 The merged harness executes 32 Z3 checks but hardcodes `TOTAL = 29`

`formal_verification_merged.py` makes **32** `check()` calls (verified: `grep -cE '^check\("CHECK' = 32`), enumerated:

```
original group  CHECK-1, 2a, 2b, 3a, 3b, 4a, 4b, 4c, 4d, 4e, 4f, 5, 5b, 5c   = 14  (labelled "12")
Kiro group      CHECK-6a, 6b, 7a, 7b, 7c, 8a, 8b, 8c, 8d, 9a, 9b, 9c          = 12  (labelled "11")
new group       CHECK-10a, 10b, 11a, 11b, 12a, 12b                            =  6  (labelled "6")  ✓
                                                                          TOTAL = 32, claimed 29
```

- `formal_verification_merged.py:477` — `TOTAL = 29  # 12 original (CHECK-1..5c) + 11 Kiro (CHECK-6..9c) + 6 new`
- `passed_count = TOTAL - len(failures)` (line 478) — the reported pass count is **derived from a hardcoded constant minus failures, not from the real number of checks run.** On a clean run it prints `Result: 29/29 checks passed` while 32 assertions actually executed (the script even prints 32 ✓ lines above that summary). On a partial failure it would misreport the denominator *and* numerator (e.g. 2 real failures → "27/29", actually 30/32).
- The exit code is still directionally correct (`exit 1` iff `len(failures) > 0`), so CI still blocks on a real failure — but the **headline artifact cited across the entire spec set is arithmetically false.**

**Irony:** the three checks that make the count wrong (`CHECK-5b`, `CHECK-5c`, `CHECK-8c`) are exactly the HANDOFF-exit-0 checks added to *fix Kiro's finding #2*. They were inserted into the "original"/"Kiro" groups without updating `TOTAL`.

**Propagation — the false "29/29" is the most-cited evidence artifact in the system:**
- `PRD_MERGED:4` — "29/29 machine-checked assertions pass, exit 0 (original 12 + Kiro's 11 reproduced + 6 new)"
- `PRD_MERGED:69`, `:125`, `:128` — repeated
- `requirements.md:358`, `:400` — "29/29 assertions passing"
- `design.md:1052` — "29/29 machine-checked (original 12 + Kiro 11 reproduced + new 6)"
- `tasks.md:847` — "29/29 checks: original 12 + Kiro 11 + new 6"

> Note: the workflow's K1 verification agent *ran* the harness and reported "29/29, exit 0 — verified by execution." That is exactly the trap: the printed number confirms the wrong claim. A human CI reviewer would be fooled identically.

### N-2 🟠 The superseded harness has the identical bug — and is still present and referenced

`formal_verification.py` makes **23** `check()` calls but hardcodes `total = 12 + 9 = 21` (`formal_verification.py:367`). So the "21" figure the merge claims to "supersede" was *itself* an undercount of 23. Both files share a systemic defect: **the reported count is a hand-maintained literal, never `len(checks)`.** The old file is still physically in the workspace and is still cited as the passing oracle in `design.md:549` and `design.md:590` (see N-3).

**Fix for N-1/N-2 (both):** replace the hardcoded total with a real counter (increment in `check()` or `TOTAL = passed_count + len(failures)` computed from actual invocations), then re-derive every "29/29" / "21/21" string from the true count (32 / 23, or a re-grouped 29 if three checks are intentionally merged). Delete or archive `formal_verification.py` so only one harness is citable.

---

## 2. Kiro's 19 findings — re-verified against current files

| # | Kiro claim (summarized) | Verdict now | Sev now | Residual (where) |
|---|---|---|---|---|
| K1 | merged harness missing; 29/29 unverifiable; CHECK-10/11/12 never encoded | **REFUTED (stale)** | RESOLVED* | *but see N-1: the "29" is wrong (32 checks); + stale `formal_verification.py` refs at `design.md:549,590` |
| K2 | HANDOFF exit-0 not in Z3; properties 8/9 don't assert exit 0 | **PARTIAL** | MEDIUM | Z3 done (CHECK-5b/5c/8c). Property tasks `tasks.md:112` (5.3) & `:118` (5.4) still assert only `status==handoff`; fix is prose-only at `tasks.md:846` |
| K3 | tasks 43–53 floating, not in dependency graph | **PARTIAL (confirmed core)** | HIGH | Tasks added (`tasks.md:851-865`) but graph still ends wave 35 / task 42.1 (`tasks.md:836`); no waves, no CI-gate registration |
| K4 | `requirement_versions`/`gate_audit_log` migrations absent from inventory; no 28.x tasks | **PARTIAL** | MEDIUM | SQL exists in addendum (`design.md:1009,1025`); Component Inventory still "six tables" (`:140`); no `007_/008_` migration files, no 28.x subtask |
| K5 | `state_integrity.py`/`audit_log.py`/`audit_verify.py` untasked | **PARTIAL** | MEDIUM | Behaviour tasked (tasks 49, 52) but never traced to those filenames; not in Component Inventory; no property test, no CI check |
| K6 | "five phases" stale | **CONFIRMED** | LOW | `tasks.md:5` AND `design.md:9` say "five"; table has 7 (Phase 0–6). Kiro's "six" is also wrong — correct is "5 required (0–4) + 2 optional" |
| K7 | 24 vs 29 properties; task 39 covers only 1–24 | **CONFIRMED (broader)** | HIGH | `design.md` defines only Property 1–24; task 39 title+subtasks+task 42 all say "24" (`tasks.md:555,668,682`); Properties 25–29 are one-line names only |
| K8 | OTel env var value not confirmed vs pinned SDK | **PARTIAL** (literal refuted) | LOW | Value is consistent (`requirements.md:231`, ref-arch); but no canonical file pins an actual OTel SDK/semconv version number |
| K9 | REQ-SPEC-016 checklist-approval has no hook home | **CONFIRMED** | MEDIUM | Hook Wiring Table (`design.md:199-202`) lists 4 PreToolUse checks; no checklist-approval enforcement point. Z3 (CHECK-12) proves the rule but nothing enforces it at runtime |
| K10 | N_PROGRESS_WINDOW not parameterized | **PARTIAL** | LOW | Harness models no-progress as a pure boolean (`Int` imported, never used; `:333`); N=3 not an integer threshold. Property test does name N=3 (`tasks.md:112`) |
| K11 | output_hash regex not asserted | **CONFIRMED** | LOW | Task 3.3 (`tasks.md:56-60`) tests "valid sha256 hash" but never asserts `^sha256:[a-f0-9]{64}$` / prefix / lowercase |
| K12 | per-file coverage tool unspecified | **PARTIAL** | LOW | SonarQube named for merge-gate; the **Verifier's** per-touched-file 85% figure (the unproven→proven input) has no generator tool / format contract |
| K13 | re-approval workflow after amendment undefined | **PARTIAL** | MEDIUM | Amendment flow specified (REQ-COV-007 / CHECK-10); but only recovery is full Initializer re-run; no light amend-and-re-approve path; amendment-SHA-mismatch not distinguished from tamper |
| K14 | `audit_verify.py` trigger unspecified | **CONFIRMED** | MEDIUM | No trigger: not SessionStart, not CI status check, not scheduled, not on-merge. Tamper-evidence is latent |
| K15 | research authority-tier schema not operationalized | **PARTIAL** | MEDIUM | Schema specified (REQ-SPEC-017 / Req 24.2); but not in `research.md` def (`:254-265`) or task 10.4; "authority tier" + "independent fact-check" undefined operationally |
| K16 | sandbox (REQ-17.4) has no design | **PARTIAL** | MEDIUM | Task 46 names tech options; but no Component Inventory entry, no chosen tech, **no design of how sandbox composes with the per-slice git worktree** (worktree ≠ security boundary) |
| K17 | gitleaks/trufflehog absent from design | **CONFIRMED** | MEDIUM | "gitleaks/trufflehog" appears only at `tasks.md:855`; not in inventory, hook wiring, or a CI workflow; design SAST = Semgrep/CodeQL only |
| K18 | verifier 5th (perf/a11y) layer not in subagent def | **PARTIAL** | MEDIUM | `verifier.md` still "all four layers" (`design.md:241`); `perf_a11y_verifier` not in inventory; task 51 cites non-existent req "9.x" |
| K19 | REASONING span kind not a standard OTel type | **CONFIRMED** | LOW | OTel `SpanKind` is a closed enum {INTERNAL,SERVER,CLIENT,PRODUCER,CONSUMER}; spec never picks attribute-vs-event-vs-name representation; no component realizes it |

**Tally:** 1 RESOLVED · 7 CONFIRMED · 11 PARTIAL · 0 false-positive.

---

## 3. New gaps Kiro missed (adversarially verified — survived a skeptic)

Grouped and de-duplicated (several were independently surfaced by 2–3 lenses — convergence ↑ confidence). Severity reflects the post-refutation adjustment.

### 🔴 High — contradictions & load-bearing omissions

- **N-3 `design.md` still points at the superseded harness.** `design.md:549` ("`formal_verification.py` already encodes 21 such checks") and `:590` (Phase-0 spine table verification column: "`python3 formal_verification.py` exits 0 (all 21 checks pass)") directly contradict `tasks.md:847`'s claim that *all* such references were repointed. *(corroborates K1 residual)*
- **N-4 REQ-STATE-005 ↔ non-blocking SessionStart contradiction.** Req 23 / CHECK-11 require the run to **block** on a resumed-state hash mismatch. But SessionStart is defined as **non-blocking everywhere** (`design.md:205` "Nothing (informational load)"; task 7.1). The integrity gate that Z3 proves has **no hook event that can fire it** — `state_integrity.py` runs at SessionStart but SessionStart cannot block. Either a different gate (a first PreToolUse check) or a documented blocking SessionStart variant is required.
- **N-5 Audit log has a table + a verifier but no PRODUCER.** REQ-AUDIT-001 mandates appending every gate decision to `gate_audit_log`. The table exists (`design.md:1025`) and `audit_verify.py` verifies the chain, but **no hook (`stop_hook.py`/`pre_tool_use_hook.py`/`subagent_stop_hook.py`) is tasked to append entries.** The chain has a reader and no writer; the audit log will be empty.
- **N-6 Hash-chain construction under-specified.** Only two SQL comments define it. No **genesis entry** (yet `prev_hash TEXT NOT NULL`), no **canonicalization rule** for "canonical form", and `entry_hash` is described as `sha256(this row || prev_hash)` while **omitting `seq`/`created_at`** — leaving ordering/reordering unprotected. Not implementable as written.
- **N-7 "in-scope" is the gate predicate but is never represented as data.** Every Stop/completion gate operates over *in-scope* items, yet neither `feature_list.json` schema nor the `coverage_items` table carries an in-scope/out-of-scope flag, and no requirement defines how an item leaves scope. The gate cannot deterministically decide which items it counts.
- **N-8 `failed` status is unreachable.** The PreToolUse status guard + Property 3 admit exactly `unproven → proven` and block all other transitions (`design.md:202`, Property 3). But the schema defines a third value `failed` (`tasks.md:27`) that Req 8.2 / Property 23 require the Verifier to write on dead checks. Direct schema-vs-gate contradiction.
- **N-9 REQ-SPEC-021 (block, exit 2) vs REQ-LOOP-005 (HANDOFF, exit 0) collide.** At the spec-completion pass cap (7) with `violation_count > 0`, Req 4.2 says block-and-continue (exit 2) while Req 4.4 + REQ-LOOP-005 say HANDOFF (exit 0). Two MUSTs, opposite exit codes, same state. Needs an explicit lex-specialis tiebreak (the docs imply 4.4 wins but never say so).
- **N-10 Criterion 10.5 (fail-closed, non-bypassable gate; ambiguous→blocked) is untasked & unmodeled.** The most load-bearing safety invariant has no implementing task, no property, and no Z3 model of an "unknown/ambiguous" gate state. `design.md:745` gives partial fail-closed prose only.
- **N-11 Sandbox (REQ-17.4) is the only runtime control against agent-executed malicious code and is undesigned.** The git worktree (a checkout) is repeatedly conflated with a security boundary. No component, no egress policy, no chosen tech, no worktree-composition design. *(sharpens K16)*
- **N-12 Cost/token budget has no numeric DEFAULT.** It is a HANDOFF trigger (`budgetExceeded`) and a hard NFR (Req 20), but unlike cap=25 / passes=7 / N=3 / retries=3, no number exists. Req 20.1's threshold registry omits it.
- **N-13 Properties 25–29 are never authored in `design.md`** (which is the document that authors property statements; stops at 24) and have **no assigned property-test file**; task 39's PBT consolidation never lists them. The property→test→CI chain is broken for all five new invariants. *(this is the deeper form of K7)*

### 🟠 Medium — wiring, count, and data-model drift

- **N-14 Postgres is "six tables" everywhere but 8 exist.** `design.md` now has 8 `CREATE TABLE` (verified); inventory (`:140`) and header (`:407`) still say "six"; tasks migration series covers 6. No migration file/number/task for `requirement_versions` or `gate_audit_log` → the migration runner cannot create the audit/amendment substrate.
- **N-15 Tasks 43–53 absent from the dependency graph** (the only machine-readable scheduling artifact). Every security/state/audit/orchestration gap-closure lives here. *(= K3, independently re-found)*
- **N-16 PRD count drift.** PRD says "20 requirements / 42 tasks / 4 phases"; canonical files have **28 / 53 / 7 (Phase 0–6)**. The PRD was never updated to its own addenda.
- **N-17 `design.md` internal phase contradiction.** `design.md:9` prose "five build phases" sits directly above a 7-row Phase 0–6 table.
- **N-18 `violation_count` has no store.** The Stop hook reads `violation_count` "from spec-completion state", but no table column / schema field / file format holds it, and the reference `evaluate_stop` never reads it.
- **N-19 Secret-scan (REQ-17.2) & chain-verifier (REQ-AUDIT-002) are tasked but wired to no CI workflow / required status check** — while sibling SAST/coverage gates ARE wired to named `.github/workflows/*.yml`.
- **N-20 Addendum components bifurcated from the normative Component Inventory.** Task 1.1's smoke test asserts "directory structure matches design component inventory" — which omits the addendum components, so the spine smoke test would pass while the new components are absent. *(this is the meta-finding in concrete form)*
- **N-21 Req 9.1 still says verification is exactly "four layers"** while REQ-VERIFY-007 adds a fifth; the acceptance criterion was never amended. *(requirements-level form of K18)*
- **N-22 `evidence_records` has no actor/agent column** but Property 24 (implementer-cannot-self-verify) must enforce from the evidence chain's acting agent; field also named inconsistently (`acting_agent` vs `actor_agent`).
- **N-23 REQ-12.4 / Property 12 baggage propagation** is realized only `on_start` for spans created within the active context; cross-process/subagent and pre-context spans are unaddressed.
- **N-24 Reasoning-loop constant K (REQ-OBS-006) is an unbound symbol** — no DEFAULT, owner, or action; omitted from the Req 20 threshold table.
- **N-25 Postgres-unavailable fallback** creates an undefined gate-consistency state for run-state-dependent checks (no-progress, cap, retry, resumed-state integrity).
- **N-26 REQ-17.5 (no secrets in prompts/spans/URLs; treat retrieved content as untrusted)** has no PreToolUse enforcement — reduced to one offline property test that cannot prevent runtime emission.
- **N-27 Retry budget (3/slice) has no owner, counter, or gate location**, unlike the cap and no-progress predicate.
- **N-28 EARS pattern set: glossary lists 6 (incl. "Complex"/"Unwanted behaviour") but schema enum + validator operate over 5** named differently. *(addendum `design.md:1048` acknowledges the "Complex" composition but the naming mismatch remains)*

### 🟡 Low — concrete code/pseudocode defects

- **N-29 `design.md` no-progress reference code would `NameError`:** it uses an undefined module constant `N_PROGRESS_WINDOW` (never assigned) shadowed by a local `run_state.no_progress_n`.
- **N-30 `check_no_progress` fires HANDOFF on a single window evaluation**, contradicting the "across the last N=3 consecutive slices" definition.
- **N-31 Hook-decision telemetry (REQ-12.3) tasked against "all five hooks"** while the system defines six; gate-decision attribute set ≠ audit-log field set.

---

## 4. Cross-document sync matrix

| Metric | requirements | design | tasks | PRD | harness | Consistent? |
|---|---|---|---|---|---|---|
| Z3 check count | "29/29" | "29/29" (`:1052`) | "29/29" (`:847`) | "29/29" (`:4`) | **32 actual / 29 hardcoded** | ❌ |
| Old harness | — | "21 checks" (`:549,590`) | superseded | superseded | **23 actual / 21 hardcoded** | ❌ |
| # requirements | **28 headings** | — | — | "20" | — | ❌ |
| # correctness properties | refs 25–29 | **24 defined** | task 39 "24" / addendum "29" | "every new req has a property" | n/a | ❌ |
| # tasks | — | — | **53 (1–42 + 43–53)** | "42" | — | ❌ |
| # waves | — | — | **36 (id 0–35), covers tasks 1–42 only** | — | — | ❌ (43–53 unscheduled) |
| # Postgres tables / migrations | — | **8 tables / "six" stated / 6 migrations** | 6 migrations | "6-table" | — | ❌ |
| # phases | "Phase 5/6 optional" | prose "five" / table 7 | prose "five" / §"Phase 4–6" | "4-phase" | — | ❌ |
| line-coverage 85% | ✓ | ✓ | ✓ | generic | — | ✅ |
| iteration cap 25 | ✓ | ✓ | ✓ | — | ✓ | ✅ |
| pass cap 7 / N=3 / retries 3 | ✓ | ✓ (retries not numeric) | ✓ | — | N as bool | ✅* |
| cost/token budget | no default | no default | no default | — | bool only | ❌ (N-12) |

**Phantom correction:** `tasks.md:848` "corrects" a "35 waves total" description that **does not exist** anywhere in the file — an artifact of a sloppy merge. (LOW)

---

## 5. What IS genuinely consistent (Kiro's green section — re-validated)

Confirmed tightly aligned across docs + market research:
`feature_list.json` JSON Schema · EvidenceRecord four-field definition · hook exit-code contract (0/1/2) · `plan-approved.json` SHA-binding · scope-sequencing gate logic (Z3 CHECK-6 + Property 7 + design pseudo-code agree) · terminal-state exclusivity COMPLETE≠HANDOFF (CHECK-3) · OPA/Conftest zero-evidence policy (Property 22) · Langfuse MIT vs Phoenix ELv2 license note · `additionalProperties:false` on EvidenceRecord · the numeric DEFAULTs 85% / 25 / 7 / N=3 / 3-retries (with the cost-budget exception, N-12). The **logic** of the new invariants (amendment monotonicity, resumed-state integrity, checklist-approval) is correctly modeled and proven in Z3 (CHECK-10/11/12) — the gaps are at the *enforcement/wiring/count* layers, not the logic layer.

---

## 6. Market-research / reference-architecture enrichment (pass 2 — additive)

Table-stakes capabilities the research/ref-arch treat as first-class that the spec set under-specifies or omits:
- **Edge-case "flag-the-omission" mechanism** — the PDF's #1 named failure mode ("agents omit required components/pages/states/edge cases *without flagging the omission*"). Spec covers the "require coverage" half (UNMAPPED gate) but not the "flag what I left out" half. *(High)*
- **Consumer-driven contract testing (Pact)** — proving components are actually wired & honor interfaces; absent.
- **Runtime structured-output schema enforcement (Pydantic/Zod/BAML/Instructor)** — named first-class by ref-arch; missing.
- **Eval-gating-in-CI** — research explicitly flags that Langfuse/Phoenix do *not* gate; no eval-gate requirement/tool/task exists.
- **Progressive delivery / feature-flag kill-switch (LaunchDarkly/OpenFeature)** for shipping agent-generated code; omitted.
- **DAST / OWASP ZAP + native `/security-review`** — named in research, missing from the security layer.
- **Tamper-evidence mechanisms (immudb / Hyperledger / hash-chain)** specified for REQ-AUDIT without a verifiable check (the research's weakest-covered category — and our N-5/N-6 confirm it).

---

## 7. To enrich / confirm next (assumptions & unknowns)

- **Z3 not installed locally** — the harness could not be executed in this workspace; the 32-vs-29 finding is by static enumeration (grep + manual). CI (which installs `z3-solver`) would print the buggy "29/29".
- The "wave scheduler" is assumed but **no orchestrator code exists** in either directory — this is a spec-only doc set, so "tasks 43–53 won't be scheduled" is a *spec-contract* gap, not an observed runtime drop (severity capped accordingly).
- OTel semconv pinned version (K8) needs confirmation against the actual `requirements.txt`/SDK once it exists.
- One workflow sub-agent miscounted the merged harness "original group" as 18 assertions; the correct enumeration is **14 + 12 + 6 = 32** (verified by `grep -cE '^check\("CHECK'`). Use 32.
