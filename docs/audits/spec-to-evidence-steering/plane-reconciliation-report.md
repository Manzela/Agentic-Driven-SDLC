# Plane Reconciliation Report — Spec-to-Evidence Governance Spine

> **WF5 deliverable.** The final reconciliation between the steering-spine audit (the
> `docs/audits/spec-to-evidence-steering/` chain) and the Plane board (epics E1-E8, phases 0-6,
> 60 stories + their tasks per `.provision_state.json`). It turns the audit's findings, gaps,
> contradictions, redundancies, and loop/token-waste risks into a verified, execution-ready board.
>
> Companion machine plan: [`plane-upsert-plan.json`](./plane-upsert-plan.json) — idempotent,
> upsert-by-NAME, safe apply order, NO deletions.
>
> Verified against on-disk source on branch `spec-reconciliation` (`b2fa9bc`), date 2026-06-18.

---

## 0. ⛔ Headline — the board is NOT execution-ready as it stands

The board describes a firing governance spine; **the spine has never fired.** Verified on disk
this session:

| Claim on the board | On-disk reality (`b2fa9bc`) |
|---|---|
| Six-hook spine registered & firing | `.claude/settings.json` **ABSENT** — Claude Code registered nothing; ralph-loop `stop-hook.sh` silently owned the Stop event |
| Four subagent base-prompts authored | `.claude/agents/` holds only `.gitkeep` — **no actor** for any verifier gate to recognize |
| Root durable-invariant anchor exists | repo-root `CLAUDE.md` **ABSENT** — every "see actor-independence in CLAUDE.md" short-name reference dangles |
| Eight `.kiro` migrations 001-008 apply (REQ-INFRA-005 AC#4) | **ZERO `*.sql` files** exist anywhere in-repo |
| `run_state` counters drive HANDOFF/cap/budget | **no populator** — `block_streak`, `external_blocker`, `no_progress_n`, `iteration_count`, `budget_exceeded`, `violation_count`, `resume_state_hash` are never written |
| Stories in Done / In-Verification / Agent-Executing | status claims **outrun on-disk reality** — the underlying tools/migrations/telemetry are absent |

What **does** exist on disk and is load-bearing: three hooks (`stop_hook.py`,
`pre_tool_use_hook.py`, `subagent_stop_hook.py`), `tools/actor_identity.py`,
`tools/evidence_collector.py`, `tools/feature_list_check.py` (225 lines, live A6 `.json` leg),
`schema/feature_list.schema.json` (already implements the four-field EvidenceRecord + the
WIRING→integration and nfr_subtype/subtype/declared_states allOf), and the nine staged remediation
artifacts under `audit/steering-audit/proposed/{00…09}`.

**The fix is the audit's thesis: register the spine once (A1), on the run branch in the run cwd,
and the majority of the symptom surface collapses.** This reconciliation lands that thesis on the
board: it creates the **13 missing owning items** for the load-bearing artifacts/prereqs that have
no home, rewrites the **14 contradictory ACs** that assert un-built state, reframes the **redundant
work** as verify-and-extend, and records the **D10/D11 scope decision** so the board stops
presupposing deferred enforcement.

---

## 1. Executive summary

- **Coverage at the finding level:** 17 of 18 transcript-forensics findings RESOLVED, **1 PARTIAL**
  (A-AMBIG-01 resume-integrity half, gated on the PreCompact prereq D7). The 4 P2 doctrines are
  RESOLVED-as-staged-doctrine in `09-CLAUDE.md`. All 7 P0s RESOLVED **subject to apply-time
  conditions** (COH-1 actor-name reconciliation; A1 on the run branch/cwd).
- **The gap the audit found but the board never owned:** the seven uncovered artifacts (00-charter,
  A1 settings.json, A5 session_start, A6 post_tool_use, A7 base-prompts, A8 goal-directive,
  A9 CLAUDE.md) and five uncovered prereqs (D3 run_state populator, `tools/execution_bounds`,
  D7 PreCompact, `tools/spec_validator.py`, ralph-loop disable/scope) are built **piecemeal across
  story tasks with no single owning item** — so none of the consuming stories is execution-ready.
- **This reconciliation creates 14 NEW owning items** (one per load-bearing orphan + three
  board-integrity/traceability items — see §5) and **updates 25 existing items** (rewrite
  contradictory ACs, reframe redundant work, carry the COH-1 literal, record the D10/D11 decision,
  true-up outrun statuses); the E7 status true-up applies to six stories under one op. **Deletions are
  zero.** (Exact machine counts in `plane-upsert-plan.json._meta.counts`: `{new: 14, update: 25}`.)
  Every entry in the task's `new_items_needed` payload maps to exactly one owning op (see
  `_meta.coverage_note`): the formal 00-charter deliverable (**NEW-13**), the cross-epic
  dependency-edge integrity item (**NEW-14**), and the disable/teardown success-oracle (**NEW-06**)
  are now owned items rather than doctrine-only mentions.
- **The one hard gate that blocks everything:** **COH-1** — the actor literal on disk is
  `verifier.md` (`tools/actor_identity.py` resolves `actor_agent` from `CLAUDE_AGENT_NAME`; the live
  hooks compare against `"verifier.md"`). The four agent frontmatters and the A4/A3 defaults MUST
  carry `name: verifier.md` byte-for-byte, or every legitimate proven-flip is blocked
  `actor_not_verifier` (fail-closed-but-stuck). This is **apply-step-0** and is encoded as a
  testable AC on the new A7 item (NEW-07) and a CI assert.
- **Loop / token-waste posture:** the 49× re-injection (C-LOOP-04) was the ralph-loop plugin owning
  the Stop event. The fix is the A1 `enabledPlugins` disable + the A2 reentrancy guard, made a
  pass/fail runtime telemetry gate on E8-13 (post-apply verification step 5). Anti-loop convergence
  (cap/budget/no-progress→HANDOFF) is inert until the D3 run_state populator (NEW-02) writes the
  counters — this reconciliation gives that populator an owning story for the first time.

---

## 2. Per-epic verdicts

Legend — **READY**: all owning items exist and ACs are testable as-on-disk. **BLOCKED**: a missing
owning item or a contradictory AC must be resolved first. **PARTIAL**: ready except for one named
prereq.

> **Cross-epic (board-integrity) — the systemic edge.** Across E2-E7 every per-story analysis returned
> `!CONTRA:NONE` on substance: **no story logically contradicts an audit conclusion** — none assumes
> the spine is *wired by design*, none invokes the phantom `field` predicate, none permits
> self-grading. The recurring finding is a *subtle inert-spine assumption*: gate-bearing ACs are
> written as if hooks fire (E4-S1 AC4/AC5 describe `pre_tool_use` behavior; E7-REQ12 "extend all six
> hooks to emit OTel" presumes a live spine). These are **unstated cross-epic dependencies on E8-13
> (settings.json) + the ralph-loop disable — `blocked-by`, not `contradicted`.** **NEW-14** turns that
> assumption into enforced board topology (explicit blocked-by edges) so apply order cannot schedule a
> hook-consuming story ahead of the registration that makes its hooks exist. E1-INFRA-008 keeping a
> human/script readiness oracle (not self-grading) is noted as a **positive alignment**, not a defect.

| Epic | Module | Verdict | Why | Items this plan adds / fixes |
|---|---|---|---|---|
| **E1** Core Plane Infra & Self-Hosting | `aea226e9` | **BLOCKED** | REQ-INFRA-005 AC#4 asserts eight migrations 001-008 apply; **zero `.sql` files exist**. The durable home for D3 (`run_state`) + hash-chained `gate_audit_log` is unbuilt. | NEW-12 (author 8 migrations + run_state completeness + append-only grant); UPD REQ-INFRA-005 |
| **E2** Agentic Workspace & Governance | `72fa8cad` | **BLOCKED** | A8 (goal-directive) and A9 (root CLAUDE.md) have **no owning story**; E2-S1/S2/S3 ACs presuppose a firing spine + verifier.md actor that don't exist; E2-S3 lists deepeval as a completion gate (charter violation) + a double-sourced static 7-check list. | NEW-03 (A8), NEW-04 (A9), NEW-05 (A7 unit + COH-1); UPD E2-S1/S2/S3 |
| **E3** Intent→Spec Compilation & Coverage | `02c58c46` | **BLOCKED** | `tools/spec_validator.py` (the single named shared prereq for E3-1/-2/-4) and `tools/execution_bounds` are **absent on disk**; every E3 story assumes a live webhook board + firing hooks. | NEW-08 (spec_validator), NEW-09 (execution_bounds — prefer fold into E8-20); UPD E3-1/-2/-4/-5/-22 |
| **E4** Verification Engine & Evidence | `b394a754` | **PARTIAL** | The single A6 PostToolUse hook is split across E4-S2 (wiring) + E4-S3 (five-layer) with **no item owning the unified hook**; schema work already on disk is presented as net-new; `evidence_collector.collect()` on-disk signature lacks `evidence_kind`/`actor_agent`. | NEW-10 (unified A6 hook); UPD E4-S1/S2/S3/S4 (reframe verify-and-extend; spine-precondition note) |
| **E5** Loop Control & Anti-Loopmaxxing | `aa9c9807` | **BLOCKED** | E5-S10 (Stop completion gate) assumes the spine is wired, names neither the A1 registration precondition, the ralph disable, nor COH-1; references `check_no_progress N=3` counters that are **inert until D3**; omits the CH-10 escalate-don't-re-inject rung. E5-S31 has a phase:2-vs-Phase-4 contradiction. | UPD E5-S10 (add preconditions + CH-10 rung), UPD E5-S31 (fix phase) |
| **E6** Workflow Routing & HITL | `ccb563fe` | **BLOCKED** | E6-S2/S3 dispatch presumes A1/A7/D10/D11/D17/D25 all exist & fire (they are staged/deferred/absent); E6-S4 seeds suffix-less agent_role values that diverge from the gate's `verifier.md` literal (COH-1); E6-S7's static check passes **vacuously** while the gates are absent. | UPD E6-S2/S3/S4/S7 (precondition notes; COH-1 vocabulary; non-vacuous guard) |
| **E7** Observability / Durable State | `b84695f2` | **PARTIAL** | The PreCompact `resume_state_hash` checkpoint hook (D7) — producer for A5's drift compare and the **only remaining PARTIAL finding** — has **no owning item**; E7 stories carry advanced states while their tools/migrations are absent. | NEW-11 (D7 PreCompact hook); UPD E7 stories (status true-up) |
| **E8** Orchestration, Anti-Loopmaxxing & HITL | `0eeab2eb` | **BLOCKED** | A5 (SessionStart canary) has **no owning story** despite being the fix for the silent-inertness root of all P0s; the D3 run_state populator (audit's #1 deferred prereq) has **no owning story**; E8-13 (A1 master fix) carries `state=Agent-Executing` while it IS the wiring that makes a spine exist (self-contradiction), and the ralph-disable + Stop-ownership telemetry is only implied. | NEW-01 (A5 canary), NEW-02 (D3 populator + BLOCKED-ON parser); UPD E8-13 (state, ralph telemetry AC), UPD E8-14/20/21 |

---

## 3. Coverage matrices

### 3.1 Finding coverage (18 transcript-forensics findings)

| Finding (P) | Resolved by (artifacts) | Owning board item after this plan | Status |
|---|---|---|---|
| A-HOOK-01 (P0) wrong/no Stop hook | A1 + A5 canary | E8-13 (A1), **NEW-01** (A5) | RESOLVED |
| A-INTENT-01 (P0) six-hook spine inert | A1, A3, A5 | E8-13, ASCP-E3-1/-2, **NEW-01** | RESOLVED |
| B-INTENT-01 (P0) settings.json off run branch | A1, A5 | E8-13, **NEW-01** | RESOLVED (apply-step-1 caveat) |
| B-INTENT-02 (P0) four base-prompts absent | A7, A4 | **NEW-05** (A7 unit + COH-1), ASCP-E4-S1/S3 | RESOLVED (after COH-1) |
| B-HOOK-01 (P0) generic stop-hook.sh took the slot | A1 | E8-13 | RESOLVED |
| C-HOOK-01 (P0) ralph Stop hook fired session | A1, A2 | E8-13 (ralph telemetry AC), ASCP-E5-S10 | RESOLVED |
| C-INTENT-02 (P0) 0/6 hooks ran; cwd split | A1, A5 | E8-13, **NEW-01**, **NEW-10** (A6) | RESOLVED (apply-step-1 caveat) |
| C-LOOP-04 (P0) 49× re-injection | A2, A4, A1 | E8-13 (ralph disable), ASCP-E5-S10, ASCP-E8-21 | RESOLVED |
| C-IDLE-03 (P0) idle vs HANDOFF | A2, A8, A4 | **NEW-02** (D3), **NEW-03** (A8), ASCP-E8-21 | RESOLVED (behavior live after D3) |
| A-IDLE-01 (P1) hand-crank terminal | A8, A2 | **NEW-03** (A8) | RESOLVED |
| B-IDLE-01 (P1) no autonomous forward path | A8, A2 | **NEW-03** (A8) | RESOLVED |
| C-REDUND-06 (P1) whole-suite re-run churn | A6, A3 | **NEW-10** (A6), ASCP-E3-* | RESOLVED |
| A-AMBIG-01 (P1) no canonical pin + no integrity gate | A5 (integrity), A8 (pin) | **NEW-01** (A5), **NEW-03** (A8), **NEW-11** (D7) | **PARTIAL** — integrity half gated on D7 |
| A-REDUN-01 (P2) manual re-grep | A6 | **NEW-10** (A6) | RESOLVED |
| B-REDUND-01 (P2) serial grep churn | A6, A8, A9 | **NEW-04** (A9 orient-before-grep) | RESOLVED (doctrine) |
| A-LOOP-01 (P2) no checkable success oracle | A9 (doctrine) + teardown oracle | **NEW-04** (doctrine) + **NEW-06** (concrete disable/teardown oracle) | RESOLVED (doctrine + concrete oracle) |
| B-AMBIG-01 (P2) named non-existent target | A9 | **NEW-04** (A9 hedge-on-named-targets) | RESOLVED (doctrine) |
| B-OVERSPEC-01 (P2) non-gating ruff treated as gate | A6, A9 | **NEW-10** (A6), **NEW-04** (A9 advisory-vs-gating-lint) | RESOLVED (doctrine) |

**Totals:** 17 RESOLVED, 1 PARTIAL (A-AMBIG-01 integrity half / D7), 0 DEFERRED. All 7 P0s
RESOLVED subject to COH-1 + apply-step-1.

### 3.2 Artifact coverage (7 uncovered artifacts → owning items)

| Artifact | What it is | Was orphaned because | New owning item |
|---|---|---|---|
| `00-charter.md` | Tier-1 doctrine governing every steering string | PARTIAL — principles applied across items but the tier-1 charter standard itself was not a formal deliverable | **NEW-13** (formal deliverable; CH-01/06/07/08; loop/idle/self-grading items trace to it) |
| `01-settings.json` (A1) | Six-hook registration + ralph disable — the master fix | owned by E8-13, but state/ralph ACs wrong | **UPD E8-13** |
| `05-session_start_hook.py` (A5) | Spine canary + resume re-orientation + drift | **no owning story**; E8-13 registers SessionStart but no AC builds the self-check | **NEW-01** |
| `06-post_tool_use_hook.py` (A6) | Forcing-function single-file targeted check | split across E4-S2 + E4-S3, no unified owner | **NEW-10** |
| `07-agent-base-prompts` (A7) | verifier/implementer/initializer/research + COH-1 names | authoring scattered across E3/E4 tasks, no unit owner | **NEW-05** |
| `08-goal-directive` (A8) | Bounded autonomy + BLOCKED-ON sentinel | **no owning story**; E2-S3 touches HITL but not the directive | **NEW-03** |
| `09-CLAUDE.md` (A9) | Durable-invariant anchor + 4 P2 doctrines | **no owning story** + no root CLAUDE.md on disk | **NEW-04** |

### 3.3 Prerequisite coverage (5 uncovered prereqs → owning items)

| Prereq | Consumed by | Was orphaned because | New owning item |
|---|---|---|---|
| **D3 loop driver / run_state populator** | A2/A4 (E8-14/21), E5-S10, E3-4, E4-S1, E6-S2/S3/S5 | the audit's #1 deferred prereq; E8-14 owns only the column migration, **nothing writes the counters** | **NEW-02** |
| **`tools/execution_bounds`** (thresholds + role registry) | E3-1/-4, E5-S10/S30, E4-S1/S3/S4, E8-14/20/21/26 | consumed via subtasks but **no item owns authoring**; absent on disk | **NEW-09** (prefer tightening **E8-20**) |
| **D7 PreCompact checkpoint hook** | A5 drift compare (NEW-01) | producer of `resume_state_hash`; **no owning item**; keeps A-AMBIG-01 PARTIAL | **NEW-11** |
| **`tools/spec_validator.py`** (Z3 EARS + vague-adj + UNMAPPED + provenance + verdict) | E3-1/-2/-4 | built piecemeal across three stories' tasks, **no single owning item**; absent on disk | **NEW-08** |
| **Ralph-loop disable / scope** | the entire Stop event | only **implied** in E8-13 `enabledPlugins`; no AC asserts runtime Stop-ownership | **UPD E8-13** (telemetry AC) |

Plus two infra prereqs surfaced by the contradictions pass:
- **Eight `.kiro` migrations 001-008** (REQ-INFRA-005 AC#4 asserts state not on disk) → **NEW-12**.
- (`tools/feature_list_check.py` is **NOT** a missing prereq — it exists on disk; A6's `.json` leg
  is live. Listed only to disambiguate from `spec_validator.py`.)

---

## 4. Contradictions & redundancies

### 4.1 Contradictions (resolved as AC rewrites, not deletions)

| # | Item | Contradiction | Resolution in this plan |
|---|---|---|---|
| C1 | ASCP-E8-13 | `state=Agent-Executing` implies an executing spine, but this story IS the wiring that makes the spine exist; AC4 presupposes a firing Stop gate it registers | **UPD E8-13** → state `Spec-Verified`/`Plan-Approved`; AC4 reworded to "after this story applies, two completion evals yield identical decision"; `agent_role=human` retained (apply is human-gated) |
| C2 | ASCP-E2-S1 | AC4 claims the 4-subagent/6-hook inner loop is reachable with integration evidence — false as-on-disk | **UPD E2-S1** → add explicit "depends on E8-13 (A1) + NEW-05 (A7) landing" precondition; reframe AC4 to assert reachability **post-spine** |
| C3 | ASCP-E2-S3 AC3 | lists deepeval among completion checks (violates "predictions never gate"); hardcodes a static 7-check list (CH-15); double-sources it (inline vs tasks.md 14.2) | **UPD E2-S3** → remove deepeval from completion gate (quality-only); source the check list from a single registry; delete the inline duplicate |
| C4 | ASCP-E2-S2 AC2 | verifier carve-out keyed on `actor_agent == verifier.md` only works if frontmatter name is `verifier.md` + CLAUDE_AGENT_NAME carries it; no agents on disk | **UPD E2-S2** → add hard dependency on **NEW-05** (COH-1 reconciliation) |
| C5 | ASCP-E3-1/-2/-3/-4/-5/-22 | every E3 task assumes a live webhook board + firing hooks; spec_validator/research_claim_validator/amendment_handler/migrations/baselines all absent | **UPD E3-*** → add "execution-ready only after NEW-08 (spec_validator) + NEW-12 (migrations) + spine (E8-13)" precondition block |
| C6 | ASCP-E3-4 AC-3 | names the Initializer as producer of `run_state.violation_count`, partially contradicting D3 (no populator exists) | **UPD E3-4** → reconcile with **NEW-02**: initializer emits via the populator, not directly |
| C7 | REQ-INFRA-005 AC#4 | claims eight `.kiro` migrations 001-008 exist & apply; zero `.sql` files exist | **UPD REQ-INFRA-005** + **NEW-12** to author the migrations so the AC is testable |
| C8 | ASCP-E5-S10 | assumes the spine is wired; names no A1 precondition, no ralph disable, no COH-1; references inert N=3 counters; omits the CH-10 escalate-don't-re-inject rung | **UPD E5-S10** → add the three preconditions + dependency on NEW-02; **add the CH-10 rung** that closes C-LOOP-04 |
| C9 | ASCP-E5-S31 | phase:2 label vs AC "Phase-4 task 40.5" | **UPD E5-S31** → set phase consistently (Phase-4 per the AC; move to `phase:4` cycle) |
| C10 | ASCP-E6-S2 | dispatch presumes A1/A7 applied + D11/D10 + kill-switch (D25) all fire; all staged/deferred/absent | **UPD E6-S2** → gate dispatch behind explicit precondition list; mark D10/D11/D25 legs deferred per §4.3 decision |
| C11 | ASCP-E6-S3 | Done-routing presumes Stop hook + OPA (D17) + GitHub required check (D17-18) triplet; none exist | **UPD E6-S3** → reframe AC to the in-scope leg (Stop hook); mark OPA/required-check legs deferred |
| C12 | ASCP-E6-S4 | seeds suffix-less `agent_role` dropdown values + `agent:coder`/`agent:tester` labels while gates need `verifier.md` literals | **UPD E6-S4** → reconcile board vocabulary with COH-1; document the `<role>.md` ↔ `agent:*` mapping |
| C13 | ASCP-E6-S7 | static "no gate reads Plane state" check passes **vacuously** while gates are absent | **UPD E6-S7** → make the check assert gates **exist AND** don't read Plane state (non-vacuous) |
| C14 | ASCP-E8-18 | asserts the plan-approval PreToolUse gate as a working exit-2 block; D10 deferred, A7 plan-approval prose-only | **UPD E8-18** → mark the enforcement leg deferred per §4.3 until D10 lands |
| C15 | ASCP-E4-S1/S2/S3/S4 | reference hooks firing as if registered; `evidence_collector.collect()` on-disk signature lacks `evidence_kind`/`actor_agent` | **UPD E4-S*** → add spine precondition; reframe the signature-extension as an explicit task (extend `collect()`), not an assumed API |
| C16 | E7 stories (REQ16/6/27/11/23/12) | advanced states (Done/In-Verification/…) while underlying tools/migrations absent | **UPD E7 stories** → true-up status to `Backlog`/`Spec-Verified` until prereqs land |

### 4.2 Redundancies (reframed as verify-and-extend, NOT deleted)

| # | Items | Redundancy | Resolution |
|---|---|---|---|
| R1 | ASCP-E4-S2 + ASCP-E4-S3 | A6 PostToolUse hook split across both, no single owner — duplicate registration | **NEW-10** builds the **one** A6 hook both stories extend; S2/S3 reframed as "extend the unified hook" |
| R2 | ASCP-E4-S2/S4 + ASCP-E3-5 | schema work already on disk (`schema/feature_list.schema.json` already has the four-field EvidenceRecord, WIRING→integration allOf, nfr_subtype/subtype/declared_states allOf) presented as net-new | **UPD** all three → reframe **verify-and-extend**, not author-from-scratch |
| R3 | ASCP-E2-S3 AC3 | completion-check list double-sourced (inline 7-check vs tasks.md 14.2) | **UPD E2-S3** (same as C3) → single-registry sourcing |
| R4 | ASCP-E6-S5 + ASCP-E6-S7 | revert-manual-Done overlaps S7 property guard | **NO ACTION** — intentional coordinated re-assertion (S7 explicitly "re-asserts E6-S5 revert"); flagged for awareness only |
| R5 | ASCP-E8-14 + ASCP-E8-21 | **both own** the Stop-hook reentrancy + HANDOFF-before-block behavior (artifact-02) and **both edit `evaluate_stop`** — overlapping ownership of one code path | **UPD-E8-14 + UPD-E8-21** carry an explicit **scope contract**: E8-14 owns the reentrancy guard (`stop_hook_active` short-circuit); E8-21 owns the escalation/HANDOFF rungs that consume `run_state` (NEW-02). Not duplication to delete — overlapping edits to one function that must be reconciled so they don't conflict. |
| R6 | E8-14/E8-21, E3-4, E4-S1, E5-S10, E6-S3 | anti-idle / HANDOFF-before-block is independently re-asserted at five layers (Stop hook, Z3 verdict, slice driver, gate, dispatch) | **NO DELETION** — appropriate **defense-in-depth**, not true redundancy. Resolution: a **single canonical HANDOFF contract** (authored in NEW-03 / charter NEW-13, referenced by all five) prevents drift; each layer cites it rather than re-stating the rungs. |

> **Layered enforcement that is intentional, not redundant (do NOT collapse).** Actor-independence /
> no-self-grading (B-INTENT-02) is enforced at many layers — E8-15/E8-29 (base-prompts), E2-S2 (write
> carve-out), E3-4 (Z3 verdict), E4-S3 (Property 24), E7-REQ16 (DB `NOT NULL`), E6-S5/S7 (Plane cannot
> manufacture `proven`). This is deliberate defense-in-depth across the stack; the reconciliation
> leaves every layer intact and (via **NEW-13**) gives them one charter clause to cite so they cannot
> drift apart.

### 4.3 Scope-mismatch decision recorded (D10 / D11)

Multiple board items (E2-S3 AC2, E4-S1 AC4/AC5, E6-S2, E8-18) treat the **plan-approval SHA-binding
gate (D10)** and **scope-sequencing (D11)** as working exit-2 blocks. The audit explicitly classes
both as **DEFERRED / out-of-scope** for the steering-string remediation; A7's plan-approval is
"prose-only / unenforced until D10 lands."

**Decision recorded by this reconciliation: mark the D10/D11 enforcement legs DEFERRED** on
E2-S3 / E4-S1 / E6-S2 / E8-18 (rather than build the PreToolUse guards now). The steering remediation
ships without them; a future Phase-2 item can add the `PreToolUse` guard that refuses the
Agent-Executing transition while `plan-approved.json` is absent or `feature_list_sha` mismatched.
This keeps the spine apply set small and avoids asserting enforcement that does not exist. NEW-07 (a
deferred-but-named placeholder for the D10/D11 guard) is created in the Backlog so the dependency is
tracked, not lost.

### 4.4 Phase / sequencing incoherences (board-integrity, NOT audit contradictions)

These are **not** logical contradictions of an audit conclusion — every per-story substance check
returned `!CONTRA:NONE`. They are internal board-integrity defects (a label disagreeing with its own
AC, an `agent_role` that does not match the work, a `state` ahead of its evidence, a `Blocked` state
with no blocker link). Listed so the reconciliation closes them, not just the content gaps.

| # | Item | Incoherence | Resolution |
|---|---|---|---|
| S1 | ASCP-E5-S31 | label `phase:2` vs AC "Phase-4 task 40.5" | **UPD-E5-S31** (C9) → cycle + label set to Phase-4 |
| S2 | ASCP-E6-S3 | dispatch leg sits at `phase:2` though required by phase:0 S2 | **UPD-E6-S3** → reframe to the in-scope Stop leg (live after E8-13); keep phase:0 ordering via **NEW-14** blocked-by edge |
| S3 | ASCP-E6-S6 | span-contract at `phase:3` though consumed by phase:0 S1; `agent_role='research'` for implementer work | **UPD-E6-S6 (recommended)** → re-phase the span-contract to match its phase:0 consumer; correct `agent_role` to the implementer role per the COH-1 `<role>.md` map (NEW-05 / UPD-E6-S4). *Captured here; executor applies the relation/field edit.* |
| S4 | ASCP-E8-19 | phase label `phase:3` contradicts its own AC (Phase 6) | **UPD-E8-19 (recommended)** → reconcile the label to the AC's Phase-6 cycle (same pattern as C9/S1). |
| S5 | ASCP-E3-22 | state-vs-`phase:2` needs reconciliation | **UPD-E3-22** (C5) already preconditions it; set the phase consistently with its phase:0 prereqs. |
| S6 | ASCP-E6-S5 | marked `Done` with **no in-slice evidence** for a blocking reconciliation item | **status true-up** → move off `Done` until evidence exists (same posture as the E7 true-up, C16); R4 overlap with S7 left intact. |
| S7 | ASCP-E7-REQ11 / REQ12 / REQ23 | recurring `agent_role:human` + `state:Agent-Executing` mismatch (a human-owned item cannot be agent-executing) | folded into **UPD-E7-STATUS** (C16) → true-up state to reflect on-disk reality; reconcile `agent_role`↔`state`. |
| S8 | ASCP-E7-REQ23 | `Blocked` state has **no encoded blocker link** | **UPD-E7-STATUS** → either encode the blocker relation (its prereq is NEW-11 / migrations) or move off `Blocked`; a `Blocked` with no edge is a dead-end in the Kanban view. |

> S3/S4/S6 are flagged for the executor as field/relation edits the apply step performs alongside the
> content UPDs; they do not require new standalone stories. They are recorded here so the
> Roadmap-by-phase and Workflow-Kanban views are internally coherent after apply.

---

## 5. NEW items (epic / phase / priority / acceptance criteria)

All NEW items are upsert-by-NAME; see `plane-upsert-plan.json` for the machine form. Priority labels
per `.provision_state.json`: `priority:blocking` / `priority:high` / `priority:normal`.

| ID | Name | Epic | Phase | Priority | Resolves |
|---|---|---|---|---|---|
| **NEW-01** | SessionStart Spine Canary & Resume Re-Orientation (A5) | E8 | Phase 0 | blocking | A-HOOK-01, A-INTENT-01, B-INTENT-01, C-INTENT-02, C-HOOK-01, B-HOOK-01, A-AMBIG-01(integrity), artifact A5 |
| **NEW-02** | Loop Driver / run_state Populator + BLOCKED-ON sentinel parser (D3) | E8 | Phase 0 | blocking | D3; unblocks C-IDLE-03, A2/A4 HANDOFF, E5-S10, E3-4 |
| **NEW-03** | Bounded-Autonomy Goal Directive + BLOCKED-ON sentinel (A8) | E2 | Phase 0 | high | A-IDLE-01, B-IDLE-01, C-IDLE-03, A-AMBIG-01(pin), artifact A8 |
| **NEW-04** | Root CLAUDE.md Durable-Invariant Anchor + 4 P2 Doctrines (A9) | E2 | Phase 0 | high | A-LOOP-01, B-AMBIG-01, B-OVERSPEC-01, B-REDUND-01, artifact A9 |
| **NEW-05** | Author the four canonical subagent base-prompts (A7) + COH-1 reconciliation | E2 | Phase 0 | blocking | B-INTENT-02, artifact A7, COH-1 |
| **NEW-08** | Author tools/spec_validator.py (Z3 EARS + vague-adj + UNMAPPED + provenance + verdict) | E3 | Phase 0 | blocking | D2(validator leg); unblocks E3-1/-2/-4 |
| **NEW-09** | tools/execution_bounds threshold + role registry | E3 (or fold into E8-20) | Phase 0 | high | execution_bounds prereq; COH-1 VERIFIER_ROLE default |
| **NEW-10** | Unify the A6 PostToolUse forcing-function (one hook both stories extend) | E4 | Phase 0 | high | C-REDUND-06, A-REDUN-01, B-OVERSPEC-01, artifact A6, R1 |
| **NEW-11** | PreCompact resume_state_hash checkpoint hook (D7) | E7 | Phase 2 | normal | A-AMBIG-01(integrity half); D7/COH-2 |
| **NEW-12** | Author eight .kiro migrations 001-008 + run_state completeness + gate_audit_log append-only grant | E1 | Phase 0 | blocking | REQ-INFRA-005 AC#4; D3 durable home |
| **NEW-13** | Author the 00-charter tier-1 base-prompt engineering standard (CH-01/06/07/08) as a formal deliverable | E8 | Phase 1 | normal | artifact 00-charter; B-INTENT-02 provenance; loop/idle traceability |
| **NEW-14** | Board-integrity: explicit blocked-by edges on E8-13 + ralph-disable from every hook-consuming story | E8 | Phase 0 | high | systemic inert-spine assumption (E1-E7 blocked-by, not contradicted) |
| **NEW-06** | Checkable success-oracle for disable/teardown tasks (kill-switch & ralph-disable) | E6 | Phase 1 | normal | A-LOOP-01 (concrete oracle for the 3-round-teardown scenario) |
| **NEW-07** | (Deferred) PreToolUse plan-approval HITL gate as enforced exit-2 block (D10) + scope-sequencing (D11) | E2 | Phase 2 | normal | D10, D11 (tracked-not-built per §4.3) |

> **NEW-06 is now an assigned owning item** (E6 kill-switch/teardown path, Phase 1) — the prior
> "intentionally not assigned" stance is superseded. The `new_items_needed` payload explicitly scopes
> a success-oracle for the *specific* disable/teardown scenario that caused A-LOOP-01's 3-round
> teardown; that is distinct from the generic checkable-success-oracle doctrine (NEW-04 AC2 / E8-20),
> so it gets its own checkable item that both UPD-E8-13 (ralph disable) and E6-S2 (kill-switch)
> cross-link. The ralph-disable + Stop-ownership telemetry remains an **UPDATE on E8-13** (AC5); NEW-06
> reuses that predicate as a reusable teardown oracle.

### 5.1 Acceptance criteria (the load-bearing few, verbatim-grade)

**NEW-01 — SessionStart Spine Canary (A5)**
- AC1: On startup/resume/compact, emits `Spine wired: 5 governance event(s) registered` (green) when
  A1's five events are registered; scope via `SPINE_REQUIRED_EVENTS` to the 5 A1 registers (COH-2), so
  the canary is green when wired *as scoped* (not a permanent PreCompact-missing yellow).
- AC2: Emits a LOUD `additionalContext` warning when the spine is unwired/partial/malformed.
- AC3: Injects re-orientation: current branch, coverage counts, last HANDOFF reason.
- AC4: Honestly emits `RESUME INTEGRITY drift detection INACTIVE` until PreCompact (NEW-11) lands — no
  silent benign branch.
- AC5: Exit 0 + stdout `additionalContext` only; fails **open** with a diagnostic.

**NEW-02 — Loop Driver / run_state Populator (D3)**
- AC1: Writes the counters each turn: `block_streak`, `external_blocker`, `no_progress_n`,
  `budget_exceeded`, `iteration_count`, `violation_count`, `resume_state_hash` (or explicitly
  down-scopes to A2's hook-owned fallback streak, recorded as a decision).
- AC2: Parses the `BLOCKED-ON: <dependency>` sentinel into `run_state.external_blocker` (the
  A8↔A2 reconciliation channel).
- AC3: After this lands, A2/A4 HANDOFF / cap / budget / no-progress paths are **live** (counters no
  longer 0); a test proves a 3-streak triggers HANDOFF, not re-injection.

**NEW-05 — Four base-prompts (A7) + COH-1** (the hard apply-step-0 gate)
- AC1: Four `.md` base-prompts authored with `name: <role>.md` frontmatter (`verifier.md`,
  `implementer.md`, `initializer.md`, `research.md`).
- AC2: `tools[]` allowlists encode: verifier = sole Evidence_Record producer / sole status→proven
  flipper; implementer = no self-grade; initializer = no self-approve, never writes
  `plan-approved.json`; research = authority tiers + non-empty `omission_declaration`.
- AC3: A CI assert proves `CLAUDE_AGENT_NAME` resolves to the literal the gates compare against
  (`verifier.md`) across `pre_tool_use_hook.py`, `subagent_stop_hook.py`, and the two spine test
  fixtures — byte-for-byte. (This is COH-1; opposite defaults re-create the G1
  fail-closed-but-stuck failure on every proven-flip.)

**NEW-08 — tools/spec_validator.py**
- AC1: One module owns Z3-backed EARS encoding, the vague-adjective proximity scanner, the UNMAPPED
  completeness check, provenance rejection, and `validate_spec()` returning a four-field structured
  verdict + a 60s timeout sentinel. E3-1/-2/-4 import it (not re-author it).

**NEW-10 — Unified A6 PostToolUse hook**
- AC1: One `06-post_tool_use_hook.py` runs ONE targeted check on the ONE changed file
  (ruff/.py, eslint/.ts·tsx·js·jsx, schema+count/feature_list.json via the on-disk
  `tools/feature_list_check.py`), feeds the located oracle + one corrective step via exit-0 JSON.
- AC2: E4-S2 (wiring leg) and E4-S3 (five-layer leg) **extend** this one hook; neither re-registers it.
- AC3: Fails **open** on its own bug / missing toolchain / timeout.

**NEW-11 — PreCompact checkpoint hook (D7)**
- AC1: On PreCompact, writes `resume_state_hash` so A5's (NEW-01) resume-integrity compare can detect
  mid-run spec mutation. Closes the only remaining PARTIAL finding (A-AMBIG-01 integrity half).

**NEW-12 — Eight .kiro migrations 001-008**
- AC1: Author/locate the eight migration files creating `requirements`, `coverage_items`,
  `traceability_links`, `evidence_records`, `run_state`, `domain_baseline_checklists`,
  `requirement_versions`, `gate_audit_log`.
- AC2: `run_state` schema carries **all** D3/D7 columns (the counters in NEW-02 + `resume_state_hash`).
- AC3: `gate_audit_log` has an append-only grant (no UPDATE/DELETE) + `requirement_id` FK integrity.
- AC4: Makes REQ-INFRA-005 AC#4 testable (the eight migrations actually apply).

**NEW-13 — 00-charter tier-1 standard (formal deliverable)**
- AC1: Lands `00-charter.md` as the tier-1 base-prompt engineering standard every steering string
  (A2/A3/A4/A7/A8/A9) inherits **by reference, not by copy**.
- AC2: Encodes CH-01 (single canonical source), CH-06 (predictions never gate), CH-07 (located oracle
  before any done-claim), CH-08 (escalate-don't-re-inject) as named, citable doctrines.
- AC3: B-INTENT-02, the loop items (C-LOOP-04 / CH-10), and the idle items (A/B/C-IDLE) each trace to
  a charter clause — provenance is no longer implicit.

**NEW-14 — Cross-epic blocked-by dependency edges (board integrity)**
- AC1: Every hook-consuming story (E2-S1/S2/S3, E3-1/-2/-4/-22, E4-S1/S2/S3/S4, E5-S10, E6-S2/S3/S7,
  E7-REQ6/11/12/16/23/27, E8-14/18/21/26) carries a blocked-by edge to E8-13 (A1 settings.json).
- AC2: The same set carries a blocked-by edge to the ralph-loop disable leg (E8-13 AC2/AC5).
- AC-NOTE: relations only — no story content/state changes; closes the systemic "gate ACs assume a
  live spine with no edge guaranteeing it" integrity gap (E1-E7 `blocked-by`, not `contradicted`).

**NEW-06 — Disable/teardown success-oracle (A-LOOP-01 concrete)**
- AC1: A checkable oracle for the ralph-loop disable (asserts `stop-hook.sh` ABSENT from telemetry;
  governance Stop hook owns the event — the UPD-E8-13 AC5 predicate, made reusable).
- AC2: A checkable oracle for the kill-switch teardown (E6-S2) — one assertion the flagd switch is OFF
  and no dispatch path remains live.
- AC3: Invoked **before** any "teardown done" claim (charter CH-07); a test proves a still-enabled
  plugin FAILS the oracle.

(Full AC text for NEW-03, NEW-04, NEW-07, NEW-09, NEW-13, NEW-14, NEW-06 is in `plane-upsert-plan.json`.)

---

## 6. View readiness

Each Plane view and whether it is execution-ready **after this plan applies**.

| View | Filter / group | Ready? | Note |
|---|---|---|---|
| 🎯 **Active Sprint** | current cycle = Phase 0 — Spine | **READY after apply** | Phase-0 now has every owning item: NEW-01/02/05/08/12 (blocking), NEW-03/04/09/10/**14** (high). **NEW-14** ensures the sprint's dependency-ordering cannot schedule a hook-consuming story ahead of E8-13. Before apply it is NOT ready — the sprint contains stories whose owning artifacts have no item. Execution order in §7 is the sprint sequence. |
| 🗺️ **Roadmap by phase** | group by cycle (Phase 0-6) | **READY after apply** | Phase 0 = the spine (incl. NEW-14 edges); Phase 1 = **NEW-13** (charter) + **NEW-06** (teardown oracle); Phase 2 = NEW-11 (D7) + NEW-07 (deferred D10/D11). The phase:2-vs-Phase-4 (E5-S31, C9/S1) and the S2-S5 phase/AC incoherences (§4.4) are reconciled. No item is phase-orphaned. |
| 🚦 **Workflow Kanban** | group by state | **READY after apply** | State true-ups remove the "outrun reality" defect: E8-13 off `Agent-Executing` (C1); E7 stories off Done/In-Verification (C16); E6-S5 off `Done`-without-evidence (S6); E7-REQ23 `Blocked`-without-link reconciled (S8); E7 `agent_role:human`+`Agent-Executing` mismatch fixed (S7). No item sits in a state its on-disk evidence cannot support. |
| 📍 **By Phase** | group by `phase:*` label | **READY after apply** | All 14 NEW items carry a `phase:*` label; E5-S31 (S1), E6-S3 (S2), E6-S6 (S3), E8-19 (S4), E3-22 (S5) label↔cycle/AC reconciled. |
| 🏛️ **By Epic** | group by module E1-E8 | **READY after apply** | Every epic gains its missing owning item(s); the per-epic verdicts in §2 all move BLOCKED→READY once the NEW items land and the UPD ACs are applied. E1 ← NEW-12; E2 ← NEW-03/04/05/07; E3 ← NEW-08/09; E4 ← NEW-10; E6 ← NEW-06; E7 ← NEW-11; E8 ← NEW-01/02/13/14. |
| 🔥 **Priority Triage** | group by `priority:*` | **READY after apply** | Triage is meaningful for the first time: the 5 `priority:blocking` items (NEW-01/02/05/08/12 + E8-13) are exactly the spine-critical path; `priority:high` is the make-it-steer-well layer (incl. NEW-14 board topology); `priority:normal` is the doctrine/deferred tail (NEW-06/07/11/13). |
| 🤖 **By Agent / Ownership** | group by `agent:*` / `human:review` | **PARTIAL until COH-1 lands** | E6-S4 seeds suffix-less `agent_role` values that diverge from the gate's `verifier.md` literal (C12); E6-S6 `agent_role='research'` for implementer work (S3). Ready only after NEW-05 + the E6-S4 vocabulary reconciliation map (`<role>.md` ↔ `agent:initializer/coder/tester/research`) + the S3 role-correction. The `agent_role=human` on E8-13 is correct (apply is human-gated). |
| 📥 **Backlog** | state = Backlog | **READY after apply** | The deferred-but-tracked items (NEW-07 D10/D11; NEW-09 conditional fallback; the E7/E6-S5 status-true-ups landing back in Backlog/Spec-Verified) live here cleanly, so nothing is silently presupposed as built. |

**Net:** 7 of 8 views are execution-ready after apply; **🤖 By Agent** is PARTIAL until COH-1
(NEW-05) + the S3 role-correction land; 🎯 **Active Sprint** is ready only once the Phase-0 NEW items
(incl. the NEW-14 edges) are created (which this plan does). Before apply, **zero** views are
execution-ready because the owning items don't exist.

---

## 7. Recommended execution order (phase-by-phase, milestone-by-milestone)

Mirrors the remediation §6 apply order, mapped onto the board. **Do not start any actor gate before
COH-1 is decided** (apply-step-0).

### Milestone 0 — COH-1 decision (apply-step-0, BLOCKING gate)
- **Decide the verifier-name convention.** On disk the literal is `verifier.md`; option (b)
  (suffix-less via `execution_bounds`) is **not currently takeable** (that module doesn't exist).
  So take **option (a): `name: verifier.md`** in the four frontmatters — zero test churn.
- Board action: this is the AC3 gate on **NEW-05**. Record the decision in NEW-05's description.

### Milestone 1 — Land the registration (Phase 0, blocking)
1. **E8-13 (UPD)** — write `.claude/settings.json` (A1); five events; ralph disabled; on the run
   branch in the run cwd. Fix the `state` contradiction (C1).
2. **NEW-12** — author the eight migrations so `run_state`/`gate_audit_log` have a durable home
   (REQ-INFRA-005 testable).
3. **NEW-14 (board-integrity edges)** — add the explicit blocked-by relations from every
   hook-consuming story to E8-13 + the ralph-disable, so the rest of the apply order cannot violate the
   spine-first topology. (Relations only; no content/state change.)

### Milestone 2 — Additive fail-open hooks (Phase 0, blocking/high)
3. **NEW-01 (A5 SessionStart canary)** — becomes the canary confirming Milestones 1/4 wired correctly.
4. **NEW-10 (A6 PostToolUse)** — the one unified forcing-function E4-S2/S3 extend.

### Milestone 3 — Actors + durable anchor (Phase 0, blocking/high) — COH-1 lands here
5. **NEW-05 (A7 base-prompts)** — author the four `.md` with `name: verifier.md`; CI assert (COH-1).
6. **NEW-04 (A9 root CLAUDE.md)** — apply alongside/ahead of the actor gates so short-name references
   resolve on first fire; carries the 4 P2 doctrines.

### Milestone 4 — Patch the reason-string hooks (Phase 0)
7. **NEW-09 / E8-20 (execution_bounds)** — author the registry first so thresholds + `VERIFIER_ROLE`
   default resolve (byte-consistent with COH-1).
8. **NEW-08 (spec_validator.py)** — so E3-1/-2/-4 become execution-ready.
9. **UPD E5-S10 / E8-21 / E8-14** (A2 Stop), **UPD E3-1/-2 + pre_tool_use** (A3), **UPD E4-S1/S3 +
   subagent_stop** (A4). Carry COH-1 into A3/A4 defaults; update lockstep tests (A4 `approve`→`allow`,
   COH-3). Run spine + property suites green.

### Milestone 5 — Run_state populator brings convergence online (Phase 0, blocking)
10. **NEW-02 (D3 populator + BLOCKED-ON parser)** — now the cap/budget/no-progress→HANDOFF paths and
    E5-S10's N=3 counters are **live**, not inert. This is the milestone that turns anti-loopmaxxing
    from designed to firing.

### Milestone 6 — Ralph telemetry + goal directive (Phase 0)
11. **E8-13 (UPD) ralph Stop-ownership telemetry AC** — verify at runtime that the governance Stop
    hook (not `stop-hook.sh`) owns the event; `stop-hook.sh` absent from telemetry (post-apply
    verification step 5, a pass/fail gate).
12. **NEW-03 (A8 goal directive)** — install as the top-level steering string; the loop now
    self-drives within the bounded-autonomy contract. Authors the canonical HANDOFF contract (R6) the
    five anti-idle layers cite.

### Milestone 7 — Phase-1 doctrine + teardown oracle (Phase 1)
13. **NEW-13 (00-charter formal deliverable)** — land the tier-1 standard so NEW-04/NEW-05 and the
    loop/idle/self-grading items cite charter clauses by id rather than re-stating them.
14. **NEW-06 (disable/teardown success-oracle)** — the concrete checkable oracle for the ralph-disable
    and the E6-S2 kill-switch teardown (closes A-LOOP-01 from doctrine to a runnable check).

### Milestone 8 — Phase-2 deferred tail
15. **NEW-11 (D7 PreCompact)** — closes the last PARTIAL finding (A-AMBIG-01 integrity half).
16. **NEW-07 (D10/D11 plan-approval guard)** — tracked in Backlog; build when accepted.

### Post-apply verification (the pass/fail gate, all must hold)
1. NEW-01 emits the green spine-wired line. 2. A PreToolUse deny on a protected-path edit carries the
R3 steering string on stderr. 3. A SubagentStop block on a self-graded record names the located
field. 4. A Stop re-entry emits zero tokens. 5. ralph `stop-hook.sh` absent from hook telemetry.
Failure of any → roll back to the pre-apply snapshot.

---

## 8. What this plan does NOT do

- **No deletions.** Every redundancy is reframed (verify-and-extend), given a scope contract (R5
  E8-14/E8-21 `evaluate_stop`), unified under one canonical contract (R6 HANDOFF), or
  flagged-for-awareness — never removed. The R4 E6-S5/S7 overlap is intentional and left intact.
- **No collapse of intentional layered enforcement.** The B-INTENT-02 / actor-independence and
  anti-idle/HANDOFF re-assertions across many layers are deliberate defense-in-depth; they are kept
  and pointed at a single citable charter clause (NEW-13) / HANDOFF contract (NEW-03), not merged.
- **No D10/D11 enforcement build.** Recorded as DEFERRED (§4.3); NEW-07 tracks it in Backlog.
- **No application to disk.** This is a board reconciliation. The actual `.claude/` writes happen via
  the remediation §6 apply order after human approval. The board changes here make that apply
  legible, ordered, and contradiction-free.

---

*Inherits `00-charter.md`, the forensics/findings deltas, and `05-remediation-spec.md` §6.
Companion machine plan: `plane-upsert-plan.json` (idempotent, upsert-by-NAME, NO deletions).*
