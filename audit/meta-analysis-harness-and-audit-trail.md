# Meta-Analysis — The Verification Harness and the Audit Trail

**Date:** 2026-06-15
**Scope (as attached):** `verification/formal_verification_merged.py` + the five `audit/*.md`
(`findings.md`, `audit-plan.md`, `verification-report.md`, `reconciliation-report.md`,
`plan-artifact-location-audit.md`).
**Method:** Direct file reads + `git show HEAD` diffing + filesystem checks + executing the harness
(z3 4.16.0 → `34/34`, exit 0) + a 6-lens adversarial-verification workflow (12 agents). Every count
below is from a command run against the working tree, not from memory or from the documents' own claims.
**One-line verdict:** The harness is the only trustworthy, drift-proof artifact here — and it certifies
a *boolean model*, not a product. The audit trail is genuinely excellent forensic work that is **already
expired**: the spec it certifies was rewritten at 20:57 (uncommitted), which (a) re-opened the count
drift the trail closed, and (b) **reintroduced the infinite-block HANDOFF defect** the committed
reconciliation had fixed — a defect the same repo's harness formally proves is impossible.

## Update — full reconciliation applied (2026-06-15)

At the user's direction, the drift documented below was reconciled to the **latest spec as source of
truth**, with the canonical value of each dimension selected by the rule *the longest enumeration is the
latest version*: **32 requirements · 30 properties · 8 tables · 34 checks · 57 tasks · 49 waves · 6 hooks
· 7 phases (0–6) · 6 EARS patterns** (5 base + Complex composition). A repo-wide survey confirmed the live
spec already holds the longest of every dimension; the only artifact shorter than the live spec was the
audit trail's EARS claim (it said 5 / "Complex removed" — false against the live 6-pattern glossary), now
corrected. Sections §0–§5 record the findings *as discovered*; this is what was then changed:

- **Infinite-block regression fixed** (`design.md` `evaluate_stop`): the HANDOFF triggers (iteration cap,
  cost budget, no-progress) are now evaluated **before** the unproven-items gate and `return allow()`
  (exit 0), and the dropped budget trigger was restored — matching Requirement 21 / REQ-LOOP-005 and
  harness CHECK-5b/5c/8c. The unproven/not-proven gate remains the only exit-2 path.
- **Count typos fixed**: `design.md:632`/`:848` and `PRD_MERGED:72`/`:77` "32 checks" → "34".
- **Coverage matrix completed**: `requirements.md` now maps Reqs 20–32 to their baseline blocks (a full
  32-requirement census; the 19 blocks remain zero-UNMAPPED).
- **Downstream artifacts aligned to 32 / 30 / 8 / 34 / 57 / 49**: `CHANGELOG.md`,
  `reconciliation-report.md` (canonical table + dated update note), `verification-report.md`
  (historical-status banner), `findings.md` / `audit-plan.md` (the "phantom `PRD_MERGED`" note corrected —
  the file now exists).
- **Harness unchanged** — it was already 1:1 with the spec's claimed count (34, self-counting) and its
  REQ-ID citations all resolve in the 32-requirement set; no edit was needed or made.
- **Verified**: harness re-run `34/34`, exit 0; grep gates for stale `22 requirement` / `39 wave` /
  `32 checks` return zero hits in the spec triad, CHANGELOG, and audit trail.

**Out of scope / left as-is:** `docs/plans/*` (website workstream — still carries a "32/32" marketing
note, a different subject per `plan-artifact-location-audit.md`). The harness's structural ceiling (a
bounded boolean model; Properties 28/29 have no Z3 oracle) is a permanent property, not drift — see §2.

---

## 0. Decisive context — the spec moved *under* the audit

The five audit files (mtime 17:xx) and the harness (16:22) certify a state the working tree no longer
matches. All three spec files were rewritten at **20:57** (uncommitted; `git status` → ` M` on each)
on a branch named `spec-reconciliation`, plus a new untracked file appeared:

| What the audit trail certifies | Live working tree (20:57) | Match? |
|---|---|---|
| `requirements.md` → **22** `### Requirement` (`reconciliation-report.md:14`, "verified") | **32** (`grep -c` → 32) | ❌ |
| `PRD_MERGED_canonical_spec_to_evidence.md` → **"does not exist anywhere"** (`verification-report.md:8`) | **exists** — 133 ln / 26 743 B, untracked, in `.kiro/specs/` | ❌ |
| `CHANGELOG.md:17` → "22 requirements … 39 dependency-graph waves" | 32 requirements; wave graph has ~49 (ids 0–48) | ❌ |
| top-level tasks (42 / "57" mixed) | **57** (`grep -c '^- \[ \] [0-9]+\.'` → 57) | n/a |
| `design.md` properties / tables | 30 / 8 | ✅ |
| harness assertions | 34 | ✅ |

This is the project's **own recurring failure mode**, recurring a third time: a "✅ APPLIED / verified"
certification that the files contradict. (First time: an earlier reconciliation-report falsely claimed
"32/32, 28 requirements, 45 waves" — caught by `verification-report.md`. Second: the current report, true
at 17:44, falsified by the 20:57 edits. The phantom `PRD_MERGED` was then "resolved" by *creating* it.)
*Fairness note:* this is uncommitted work on a reconciliation branch — the expected intermediate state, not
a shipped lie. It is "trustworthy-pending-recommit," and the next commit could refresh the counts. The
durable problem (below) is not the transient counts.

---

## 1. The 20:57 edit reintroduced the infinite-block HANDOFF defect (P0)

This is the single most important technical finding, and it is **not** transient count drift — it is a
logic regression in the design's load-bearing safety mechanism.

- **Committed HEAD (correct):** `evaluate_stop` checks the HANDOFF triggers **first** and returns
  `allow()` (exit 0): cap (`design.md` HEAD:696→698), budget (701→703), no-progress (705→707); the
  unproven/not-proven `block()` comes *after* (722→724). CHANGELOG:17 records this as
  *"Fixed the latent infinite-block HANDOFF defect … HANDOFF now exits 0, matching Z3 CHECK-5b/5c/8c."*
- **Live working tree (20:57, regressed):** the order is **reversed** — "Check 1" is now the unproven
  block (`design.md:692-696`, `return block(...)`), and the no-progress / cap `allow()` paths are
  Checks 2–3 *after* it (`:713-718`, `:720-724`).
- **Why it breaks:** HANDOFF on cap/no-progress occurs *precisely while items are still unproven* (the
  run ran out of turns before proving everything; the design even says items stay `unproven` on HANDOFF).
  With unproven-block now first, the cap-reached run returns `block()` (exit 2) → the agent is **forced
  to keep working past its cap** → the exact infinite-block the fix removed. The cap-allow at `:724` is
  unreachable.
- **It now contradicts the project's own proof.** The harness asserts `Or(cap,budget,noProgress) →
  ¬hookExitsBlocking` (core axiom) and proves `capReached ∧ blocking` UNSAT (`CHECK-5b/5c/8c`). The live
  reference code does exactly what the harness proves is impossible — yet the harness still prints
  `34/34`, because **it checks an abstract model, never this code.** (See §3, the proof paradox.)

This is reference/pseudocode in a design doc, not shipping code (nothing is built) — but it is *the*
illustrative block for the system's central guarantee, and it is wrong. The audit trail did not catch it
because the audit ran before the 20:57 edit.

---

## 2. The harness — what `34/34` actually proves

The best-engineered artifact in the repo, and the only one that resists drift by construction.

**Strengths (verified):**
- **Self-counting:** `TOTAL = checks_run` (`:506`); 34 `check()` calls (`grep -c` → 34). The reported
  count cannot drift from the real count — the property every other artifact lacks; fixes the
  hardcoded-`TOTAL` bug the trail documents (`findings.md` N-1/N-2).
- Runs green: `Result: 34/34 checks passed`, exit 0, z3 4.16.0 (executed).
- **Genuinely informative checks:** `CHECK-1` (full axiom set jointly SAT → requirements are not
  mutually contradictory — the one global, non-trivial result); `CHECK-2a/3a/4f` (naïve formulations
  UNSAT → real conflict detection); `CHECK-5` (prediction independence: `gateA==unproven ∧
  gateB==unproven ∧ predA≠predB ∧ gateA≠gateB` UNSAT — a real cross-variable proof on *fresh* symbols,
  not the core axioms); the SAT reachability family (`4a–4e, 6b, 7b, 8d, 9b, …`) proving guards can fire.

**Hard limits (verified — and the spec concedes them):**
- **Boolean abstraction; no numeric threshold is verified.** `Int` is imported but **never
  instantiated** (`grep -nE '\bInt\('` → 0). `N=3`, `85%`, `cap=25`, the cost budget, `K=3` are all
  collapsed to booleans. The shape of the invariants is proved; the quantities the guarantees rest on
  are not.
- **Zero I/O, zero product coupling.** Imports only `z3` and `sys`; 42 free `Bool` symbols; never reads
  code, DB, run-state, or evidence. It proves a *self-contained model*, not a system — and no system
  exists to check.
- **~4–5 of the 34 are near-tautological by construction.** `CHECK-9a/11a/12a/13a` (and `8c`) each add a
  one-line axiom (e.g. `Implies(resumeHashMismatch, Not(runProceeds))`) then assert its direct
  contradiction → UNSAT-by-construction. Useful as *regression guards* (weaken the axiom, the check
  flips), not as discovered properties. (`CHECK-5b/5c` run against the full 15-axiom core, so they
  *additionally* prove non-interference — not pure tautologies.)
- **The two most auditor-relevant invariants have no Z3 oracle at all.** Property 28 (audit-log
  tamper-evidence) and Property 29 (research-claim sourcing) are PBT-only by decision
  (`reconciliation-report.md:40`, "B4: No — harness stays 34"); the verifier they depend on
  (`tools/audit_verify.py`) does not exist. The literal Phase-3 "tamper-evident trace" promise has zero
  machine-checked backing.

**Net:** "34/34 machine-checked" is legitimate but modest — it certifies a *consistent boolean model of
the requirements*, not running code and not the numbers. The live spec is honest about this
("Z3 proves the logic model only," `requirements.md:499`).

---

## 3. The proof paradox — applying the product's own benchmark to the project

The product's success benchmark: *an external auditor independently verifies every requirement was
fulfilled, every invariant respected throughout, and **no self-report accepted as proof**.* The
meta-project fails its own benchmark on three counts, all verified:

1. **There is no run to audit.** 0 of 57 tasks built; the only executable artifact is the 522-line model.
2. **The oracle is not independent.** The same authorship wrote the requirements *and* the axioms
   encoding them, then checked the axioms against themselves. A faithful-but-wrong transcription passes —
   which is **exactly what §1 is**: the model says blocking-on-cap is impossible; the implementation
   sketch does it; the model stays green.
3. **The trail accepts self-report as proof.** `reconciliation-report.md:4` self-attests "✅ APPLIED …
   verified," after a *documented prior* false "applied" claim — the precise pattern the product forbids.

To the project's credit, real anti-self-report disciplines exist: the harness self-counts; the README
says "Pre-implementation"; the trail transparently brands its own predecessor a false claim. The honesty
is genuine. But honesty about a bounded, non-independent, model-only proof is not the auditor-verifiable
*delivery* the vision sells.

---

## 4. The five audit files — quality and current status

A four-layer stratigraphy of self-correction (oldest→newest):

1. **`findings.md`** *(superseded).* Earliest pass; audited the then-nonexistent `PRD_MERGED` and cited
   beyond-EOF lines; counts (32/29) wrong. **Banner-marked but never regenerated** — still physically
   contains the phantom-file refs and 4 beyond-EOF `design.md:10xx` citations (`verification-report.md`
   Batch 7 called for regeneration; only bannering was done, so "✅ APPLIED" overstates it).
2. **`audit-plan.md`** *(superseded).* Companion remediation list; same residual phantom refs.
3. **`verification-report.md`** *(authoritative — genuinely excellent).* 65-agent audit, "57 confirmed /
   0 refuted," harness executed, 4-strata drift catalogued, a canonical-target table, a 7-batch
   remediation map with explicit Class-A/B decisions, and a 10-gate **residual-drift checklist**. Model
   forensic work. Its own gate #6 (`grep -c '### Requirement' = 22`) **now fails** (live = 32).
4. **`reconciliation-report.md`** *(claims "✅ APPLIED").* Real at 17:44; falsified by the 20:57 edits.
   Its certified "22 requirements, consistent across ALL files" is the headline now-false claim.
5. **`plan-artifact-location-audit.md`** *(separate subject, correct).* A clean little audit concluding
   the **website** plan's R/D/T were inline/unmaterialized — already overtaken: `docs/website/` was
   materialized at 20:55.

**Even the certified HEAD was not fully self-consistent.** Two inconsistencies shipped into the
"canonical, verified" commit and/or its working tree:
- **Coverage matrix vs requirement body (at HEAD):** body declares `REQ-COV-001..007`
  (`requirements.md:121`) but the appendix matrix says `..006` (`:423`); likewise `REQ-LOOP-001..005`
  body vs `..004` matrix — while the matrix asserts "Zero UNMAPPED items" and enumerates only B01–B19
  (Reqs 1–19), silently omitting Reqs 20–32.
- **Harness count contradiction (live):** `design.md:632` and `:848` say "all 32 checks pass" / "32
  machine-checked assertions" while `:1181` and the harness say 34 (a 20:57-introduced residual; HEAD
  did not carry it).
- **Chain claim broken:** CHANGELOG's "closed every requirement → property → task → wave → CI chain" is
  false for the new Requirements 23–32 — they have **no** new `### Property` (still 30) and **no** Z3
  check (still 34). New IDs `REQ-EVAL-001 / REQ-SEC-008 / REQ-CTRL-001` sit outside their declared ranges.

**For fairness, the 20:57 edit also improved things:** it promoted three previously-deferred
market-research gaps into full requirements — Eval-Gating (Req 30, DeepEval), DAST (Req 31, OWASP ZAP
baseline), Kill-Switch (Req 32, OpenFeature/flagd) — so the live "deferred" set is now only Pact + runtime
structured-output enforcement. That is real gap-closure. One residual weakness: the omission-declaration
gate (Req 29 / Property 30 / CHECK-13) is **presence-only** — it rejects a *null* declaration but encodes
no completeness/honesty predicate, so a trivial non-null value (`"none"`) satisfies it. The market
research's #1 failure mode (silent omission) is half-closed, not closed.

---

## 5. Bottom line

- **Trust the harness as the count-of-record (34, self-counting)** — understanding it certifies a
  consistent boolean model of the requirements, not a product, not the numeric thresholds, and not the
  two most auditor-relevant invariants (28/29, PBT-only, verifier absent).
- **Treat the audit trail as an expired snapshot.** `verification-report.md` remains the best document;
  `reconciliation-report.md`'s "22 requirements / verified" is no longer true on disk (live 32 +
  materialized `PRD_MERGED`); `findings.md` / `audit-plan.md` are known-stale and still carry phantom +
  beyond-EOF citations; `plan-artifact-location-audit.md` is correct but off-topic and overtaken.
- **Fix the load-bearing regression first:** restore the HEAD ordering in `design.md` `evaluate_stop`
  (HANDOFF `allow()` before the unproven `block()`), and reconcile `design.md:632/848` "32"→"34". Both
  contradict the harness the project leads with.
- **The structural fix, not another reconciliation pass:** stop certifying counts in prose. Wire
  `verification-report.md`'s residual-drift checklist as a runnable hook/CI gate that *recomputes* the
  counts and cross-references on every change — i.e. apply the product's own mechanism (a deterministic,
  self-recomputing gate) to the project's own artifacts, so the audit trail can no longer outlive its
  evidence. That the trail keeps expiring within hours is the most precise possible demonstration of why
  the product it specifies would be worth building.

*This is analysis only. No spec, audit, or code file was modified.*
