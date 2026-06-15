# Spec-to-Evidence Control System — Remediation Plan

**Companion to:** `audit/findings.md`. Prioritized fix list. **No fixes applied — approval gate is open.**

## Sync verdict

> **The five artifacts are NOT yet synced/aligned.** They are internally bifurcated: a *normative core* (count claims, component inventory, dependency graph, property catalogue, hook-wiring table, phase prose) frozen at the pre-merge state, plus a *prose addendum* describing the post-merge state. The single most-cited number in the system — "29/29 machine-checked assertions" — is arithmetically false against the file it cites (32 checks). Closing the gaps requires **back-propagating each addendum into its canonical table**, not adding more prose.

Two classes of fix:
- **Class A — Reconciliation (cheap, mechanical):** make the normative core match the addendum. ~80% of findings. Mostly find/replace + table rows + graph edits. Low risk, high consistency payoff.
- **Class B — Genuine design gaps (need a decision):** contradictions and undesigned components where the addendum has no answer yet. These need a human/architect call before they can be tasked.

---

## P0 — Must fix before any "formally verified" / "29/29" claim is made

| ID | Fix | Why | Where | Class | Effort |
|---|---|---|---|---|---|
| P0-1 | Replace hardcoded `TOTAL=29` (and old `total=21`) with a counter derived from actual `check()` calls; re-derive every "29/29"/"21/21" string from the true count (32/23) — or intentionally merge 3 checks to make it genuinely 29 and document the grouping | The headline evidence artifact is false; `passed_count` is decoupled from reality (N-1, N-2) | `formal_verification_merged.py:477-478`; `formal_verification.py:367`; then `PRD_MERGED:4,69,125,128`, `requirements.md:358,400`, `design.md:1052`, `tasks.md:847` | A | S |
| P0-2 | Delete/archive `formal_verification.py`; repoint `design.md:549` and `:590` to `formal_verification_merged.py` / correct count | Two harnesses, one stale & still cited as the passing oracle (N-3); contradicts `tasks.md:847` | `formal_verification.py`, `design.md:549,590` | A | S |
| P0-3 | Resolve REQ-STATE-005 ↔ non-blocking SessionStart **contradiction**: define the enforcement point (blocking SessionStart variant, or a first-PreToolUse integrity guard) | CHECK-11 is proven but **cannot fire** — false sense of a working integrity gate (N-4) | `design.md:205`, REQ-STATE-005, `state_integrity.py` task 49 | **B** | M |
| P0-4 | Specify + task the audit-log **producer**: which hooks append to `gate_audit_log`, when | Tamper-evident log has a verifier & table but **no writer** → empty log (N-5) | hooks (`stop_hook.py` etc.), task 52 | **B** | M |
| P0-5 | Resolve REQ-SPEC-021 (exit 2) vs REQ-LOOP-005 (exit 0) exit-code collision at pass-cap-with-violations | Two MUSTs, opposite exit codes, same state (N-9) | Req 4.2 / 4.4 / REQ-LOOP-005 | **B** | S |
| P0-6 | Resolve `failed` status reachability: either allow `unproven→failed` in the status guard or remove `failed` from the schema | Schema value the Verifier must write is gate-forbidden (N-8) | `design.md:202` (status guard), Property 3, schema `tasks.md:27` | **B** | S |

## P1 — Required for the spec to be implementable & the new gates to actually gate

| ID | Fix | Why | Where | Class | Effort |
|---|---|---|---|---|---|
| P1-1 | Add tasks 43–53 to the Task Dependency Graph with wave ids + dependency edges; register CI-blocking ones (45 secrets, 52 chain-verify) as required status checks | Only machine-readable scheduler omits every security/state/audit gap-closure (K3, N-15, N-19) | `tasks.md:688-836` | A | M |
| P1-2 | Author Properties 25–29 in `design.md`; add 39.x subtasks (or task 54) + update task 39/42 titles from "24" to "29"; assign property-test files | Property→test→CI chain broken for all 5 new invariants (K7, N-13) | `design.md` §Correctness Properties; `tasks.md:555,668,682` | A | M |
| P1-3 | Add `requirement_versions`, `gate_audit_log` to the Component Inventory + create `007_/008_*.sql` migration files + a 28.x migration task; change "six tables"→"eight" | Migration runner can't create the amendment/audit substrate (K4, N-14) | `design.md:140,407`, tasks migration series | A | S |
| P1-4 | Add `state_integrity.py`, `audit_log.py`, `audit_verify.py`, `perf_a11y_verifier` to the Component Inventory with file paths/phases; trace tasks 49/52/51 to those filenames | Spine smoke test (task 1.1) asserts against the inventory and would miss them (K5, N-20) | `design.md:122-145`, tasks 49/51/52 | A | S |
| P1-5 | Fully specify the hash chain: genesis entry, canonicalization rule, include `seq`+`created_at` in `entry_hash`, and the verification **trigger** (SessionStart? merge? CI?) | Not implementable as written; tamper-evidence latent (N-6, K14) | `design.md:1024-1037`, REQ-AUDIT, `audit_verify.py` | **B** | M |
| P1-6 | Add a checklist-approval enforcement row to the Hook Wiring Table (PreToolUse or discovery-time guard) | REQ-SPEC-016 proven in Z3 but unenforced at runtime (K9) | `design.md:194-206` | A/B | S |
| P1-7 | Define "in-scope" as data: add an `in_scope`/scope field to schema + `coverage_items`, and a requirement for how items leave scope | Gate predicate has no data backing (N-7) | schema, Postgres `coverage_items`, new req | **B** | M |
| P1-8 | Design the sandbox (REQ-17.4): choose tech, define egress policy, specify worktree composition; add Component Inventory entry | Only runtime control vs malicious agent code is undesigned (K16, N-11) | `design.md` inventory, task 46 | **B** | M |
| P1-9 | Add gitleaks/trufflehog to design inventory + a `.github/workflows/secrets-scan.yml` as required status check; pick one tool | Secret scanning exists only as one task line (K17, N-19) | `design.md`, `tasks.md:855` | A | S |
| P1-10 | Update the Verifier subagent definition + Req 9.1 to the 5-layer model (add perf/a11y); add `perf_a11y_verifier`; fix task 51's "9.x"→concrete criteria | Verifier def & Req 9.1 still say "four layers" (K18, N-21) | `design.md:241`, Req 9.1, task 51 | A | S |
| P1-11 | Define the `violation_count` store (table column or schema field) and have `evaluate_stop` read it | Stop hook depends on a value nothing persists (N-18) | schema/`run_state`, `design.md` evaluate_stop | A/B | S |
| P1-12 | Add numeric DEFAULTs for cost/token budget, reasoning-loop K, and retry-budget owner/counter to the Req 20 threshold registry | HANDOFF triggers/NFRs with no number (N-12, N-24, N-27) | Req 20.1, REQ-OBS-006 | A/B | S |
| P1-13 | Decide REASONING-span representation (custom attribute on INTERNAL span vs span event vs name convention); name the component | OTel SpanKind is a closed enum — current spec is unrealizable (K19, N-31 attr-set) | `design.md:1044`, REQ-OBS-006 | **B** | S |

## P2 — Consistency hygiene & robustness

| ID | Fix | Where | Class |
|---|---|---|---|
| P2-1 | Phase wording → "5 required (0–4) + 2 optional (5–6)" | `tasks.md:5`, `design.md:9`, PRD "4-phase" (K6, N-17) | A |
| P2-2 | PRD count refresh: 20→28 req, 42→53 tasks, 4→7 phases | PRD (N-16) | A |
| P2-3 | Assert `output_hash` regex `^sha256:[a-f0-9]{64}$` (anchored, lowercase, prefix) in task 3.3 + a property | `tasks.md:56-60` (K11) | A |
| P2-4 | Add exit-0-on-HANDOFF assertion to property tasks 5.3/5.4 | `tasks.md:112,118` (K2) | A |
| P2-5 | Parameterize N as an integer threshold in harness + property test; fix `check_no_progress` single-window vs N=3 | harness `:333`, design pseudo-code (K10, N-30) | A |
| P2-6 | Specify the Verifier's per-touched-file coverage generator + output format (pytest-cov?) | design, Req 9.6 (K12) | A/B |
| P2-7 | Define light amend-and-re-approve path; distinguish amendment-SHA-mismatch from tamper | `design.md` plan-approved gate (K13) | B |
| P2-8 | Operationalize authority-tier taxonomy + fact-check tooling; wire into `research.md` + task 10.4 | `design.md:254-265`, task 10.4 (K15, N-22 actor) | A/B |
| P2-9 | Fix `N_PROGRESS_WINDOW` NameError in pseudo-code; reconcile `acting_agent`/`actor_agent`; "five hooks"→six; baggage cross-process propagation; Postgres-unavailable fallback state; EARS 6-vs-5 naming; pin OTel version; remove phantom "35 waves" correction | various (N-22, N-23, N-25, N-28, N-29, K8, phantom) | A |

## P3 — Market-research enrichment (new requirements, optional for v1 scope)

Eval-gating-in-CI · consumer-driven contract testing (Pact) · runtime structured-output schema enforcement (Pydantic/BAML) · the edge-case **flag-the-omission** mechanism (research's #1 failure mode) · DAST/OWASP ZAP · progressive-delivery kill-switch. Decide in/out of v1 scope; if out, add to the explicit out-of-scope list with rationale (the system's own discipline).

---

## Suggested execution order

1. **P0 batch** (6 items) — stop claiming "verified" until the count is real and the 4 contradictions (P0-3..6) have a decision.
2. **Class-A reconciliation sweep** (P1-1..4, P1-9..12, all P2-A) — one editing pass that back-propagates every addendum into its canonical table/graph. Low risk; restores internal consistency.
3. **Class-B design decisions** (P0-3..6, P1-5, P1-7, P1-8, P1-13, P2-7) — need an architect call; each becomes a small design note + task.
4. **P3** — scope decision.

**Recommendation:** start with the P0 batch (especially P0-1, the count fix) and the Class-A sweep — together they remove ~80% of the findings and make the doc set self-consistent. Then schedule the Class-B design decisions, which are the genuinely open questions Kiro's analysis (and the merge) never resolved.
