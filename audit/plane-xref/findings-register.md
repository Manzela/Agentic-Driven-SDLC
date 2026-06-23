# Cross-reference findings register — Plane board ⇄ spec-to-evidence steering audit

> Deepening/verification pass on `spec-reconciliation` (2026-06-18), run AFTER the prior reconciliation
> (243→256). 10-axis fan-out → 56 verified findings (52 confirmed/revised). Raw per-finding detail:
> [`findings-compact.md`](./findings-compact.md). Machine delta: [`delta-plan.json`](./delta-plan.json).
> Verified findings (full): [`verified-findings.json`](./verified-findings.json).

## The meta-root-cause (why "the report says resolved" ≠ "the board is resolved")

The prior reconciliation **authored** a sound plan but its **applier silently dropped fields**. The
board's API has no native acceptance-criteria field, and `apply_upsert_plan.py` only PATCHed
`description_html` / `state` / `labels`. So three classes of intended content never reached the board:

1. **`acceptance_criteria` (39/39 ops)** — the *testable* criteria that make an item executable.
2. **`priority` (39/39 ops)** — broke Priority-Triage.
3. **`additional_match_keys`** — the 7-target E7/E6-S5 status true-up hit only 1 target.

Plus two the applier *structurally* cannot do: **relations** (NEW-14's whole dependency topology) and a
**create that collides by match_key** (NEW-12 merged onto REQ-INFRA-005 and was overwritten).

**Important nuance discovered live:** between this pass's first snapshot (17:48) and synthesis (18:30),
one workflow sub-agent **edited `apply_upsert_plan.py` to fold ACs + priority and re-ran it**, fixing
classes 1–3 — and in doing so **deleted the NEW-09 duplicate** and **overwrote 6 stories' descriptions**
with an identical generic note (content loss). So several "still-broken" findings were *real at
finding-time but already fixed* by the time of apply; this register marks those honestly.

## Status legend
- **FIXED-MIDRUN** — real at 17:48, fixed by the sub-agent's 18:30 applier re-run (ACs/priority/state).
- **FIXED-DELTA** — fixed by this pass's `apply_delta.py` run (NEW-12, relations, restores, hook-design ACs).
- **REFUTED** — contradicted by live board data (verify agent worked off stale/mid-run state).
- **RESIDUAL** — left open with rationale (verify-before-trust, or low-value/doc-only).

## Coverage / traceability
| id | sev | status | note |
|---|---|---|---|
| COV-01 / XC-03 | P0 | **FIXED-DELTA** | NEW-12 never existed (collided onto REQ-INFRA-005). Created standalone at seq 264 (E1/Phase 0/blocking) with its 4 migration ACs; REQ-INFRA-005 AC#4 now references a real owner. |
| COV-02 / PSD-01 | P0 | **FIXED-DELTA** | Total relation vacuum. 25 `blocked_by` edges to E8-13 created; E8-13 now shows 25 `blocking`. |
| COV-03 / COV-04 | P1 | **FIXED-MIDRUN** (partial RESIDUAL) | E7/E6-S5 true-ups landed on all 7 at 18:30. The *further* advanced-state items (E8-15/E8-19/E5-S17/S30/S32/E6-S6) are **RESIDUAL — verify-before-trust** (some hooks/tools DO exist on disk, so not all are evidence-impossible). |
| COV-05 / HGD-6 / AI-05 | P2 | **FIXED-DELTA** | `execution_bounds` double-owned (NEW-09 + E8-20). NEW-09 removed (dedup); E8-20 is sole owner. |
| COV-06 | P2 | **FIXED-DELTA** | D7/PreCompact double-owned (NEW-11 + E7-REQ11.3). `relates_to` edge + scope note added; distinct legs. |

## Contradictions / apply-integrity
| id | sev | status | note |
|---|---|---|---|
| XC-02 / RED-01 / AO-01 / AO-02 | P0 | **FIXED-MIDRUN** | `acceptance_criteria` dropped for all ops → items oracle-free. Folded into `description_html` at 18:30 (NEW-05 639→1498 chars w/ AC1–AC4). |
| AI-03 / WF-01 / XC-01 / PSD-02 | P0/P1 | **FIXED-MIDRUN** | `additional_match_keys` ignored → 1-of-7 true-up. All 7 (REQ6/11/12/23/27, E6-S5, REQ16) now in Backlog. |
| AI-04 | P1 | **FIXED-MIDRUN** | priority dropped on creates → now urgent/high/medium set correctly across the 13. |
| AI-06 | P2 | **RESIDUAL** | `.apply_log.json` is a plan-echo (no per-op HTTP outcome). Superseded by `.apply_delta_log.json` for this pass; recommend per-op result logging going forward. |
| AI-07 | P2 | **RESIDUAL** | E6-S6 (phase-label↔AC) and E8-19 (phase:3↔Phase-6 AC) phase incoherence — recorded; low-value field edits, deferred. |
| XC-05 | P1 | **FIXED-DELTA** | E8-13 parent/child PreCompact contradiction → G4 AC clarifies 5 events; PreCompact is NEW-11, scoped out of A1 register (COH-2). |
| XC-06 | P2 | **RESIDUAL (mitigated)** | Phase-0 spec-complete items sit Spec-Verified while prereqs aren't green; the new `blocked_by` edges now make the dependency explicit, so the state is no longer a silent claim. |

## State / workflow integrity
| id | sev | status | note |
|---|---|---|---|
| WF-01 / WF-05 | P0/P1 | **FIXED-MIDRUN** (residual flagged) | C16/S6/S7/S8 true-ups landed on the 7 named; the broader set is the COV-04 RESIDUAL. |
| WF-02 (REQ23 Blocked-no-link) | P1 | **REFUTED→FIXED** | Live: REQ23 moved Blocked→Backlog at 18:30; board now has **0 Blocked** items. The dead-end is gone. |
| WF-03 (REQ11/12 Agent-Executing) | P1 | **REFUTED→FIXED** | Live: both moved to Backlog at 18:30 (finding was stale). |
| WF-04 (E6-S5 Done-no-evidence) | P1 | **FIXED-MIDRUN + restored** | Moved Done→Backlog; its over-written description was **restored** (G1) so it isn't a generic stub. |
| WF-06 | P2 | **RESIDUAL** | "Kanban READY" verdict was premature; materially improved (0 Blocked, states reconciled), full readiness still gated on the spine actually being built. |

## Redundancy / phase-deps
| id | sev | status | note |
|---|---|---|---|
| RED (R1) | P1 | **FIXED-DELTA** | E4-S2/E4-S3 now `blocked_by` NEW-10 (extend-not-re-register the one A6 hook). |
| RED (R5) | P0/P1 | **FIXED-DELTA** | E8-14 `relates_to` E8-21 + G4 scope contract: E8-14=reentrancy short-circuit, E8-21=escalation rungs. |
| RED (R6) | P1 | **FIXED-DELTA** | 5 anti-idle layers (E8-14/E8-21/E3-4/E5-S10/E6-S3) `relates_to` NEW-03 (single canonical HANDOFF contract). |
| PSD-03 / PSD-04 / AO-04 / HGD-5 / TWL-08 | P0/P1 | **FIXED-DELTA** | All the "edge dereferences to nothing" findings closed by the 40 real relations now on the board. |

## Token-waste / loop-prevention (the autonomous-steering core)
| id | sev | status | note |
|---|---|---|---|
| TWL-01 | P0 | **FIXED-DELTA** | CH-10 escalate-don't-re-inject rung added as a *testable* AC on E5-S10 (Stop re-entry emits ZERO tokens; 3-streak→HANDOFF, not the 49× re-injection). |
| TWL-02 / TWL-04 / BP-2 | P0/P1 | **FIXED-DELTA** | Reentrancy guard re-specced onto the **hook-input `stop_hook_active` payload flag** (not a self-authored run_state mutex that races the loop); ownership split E8-14↔E8-21 (R5). |
| TWL-03 | P0 | **FIXED-DELTA** | NEW-02 (D3 populator) now has `blocked_by`-edges *from* E5-S10/E3-4/E8-21 (HANDOFF/counter consumers); its ACs landed mid-run. |
| TWL-06 | P1 | **FIXED-DELTA** | E8-13 G4 AC adds the ralph-disable runtime telemetry assert (stop-hook.sh absent from telemetry post-apply). |
| TWL-05 / TWL-07 | P2 | **RESIDUAL** | Charter clause-number mislabel (CH-08 vs CH-10) + NEW-10 prose-stub; NEW-10 now has R1 edges, AC-text polish deferred. |

## Hook generalization & dynamism (the "agent fights the hook" concern)
| id | sev | status | note |
|---|---|---|---|
| HGD-1 / BP-3 | P0/P1 | **FIXED-DELTA** | **Exit-2 steering reason must go to STDERR, not stdout** — Claude reads stderr on a block; stdout+exit2 makes the steer invisible → the agent flails. Added as E8-13 G4 AC + content-diff (phantom-field) ownership. |
| HGD-2 | P0 | **FIXED-DELTA** | PreToolUse matcher was `Write\|Edit\|MultiEdit` only → protected paths editable via `Bash` (`sed`/`tee`/`echo>`). G4 AC: matcher must include Bash + a content-level path check. |
| HGD-3 | P0 | **FIXED-DELTA** | COH-1 `verifier.md` literal is brittle (byte-for-byte across files). G4 AC on NEW-05: resolve via one `VERIFIER_ROLE` constant/env so a rename is one line. |
| HGD-4 / BP-4 | P1/P2 | **FIXED-DELTA** | SubagentStop trusted a *payload* `actor_agent` (spoofable) and returned `decision:"approve"` (not a valid SubagentStop value). G4 AC on E4-S1: resolve actor from `CLAUDE_AGENT_NAME` server-side; decision `"block"`/omit. |
| BP-1 | P0 | **FIXED-DELTA** | settings AC said 6 hooks + PreCompact + matcher 'Write'; corrected to the 5 A1 events (COH-2). |
| BP-5 | P3 | **RESIDUAL** | best-practices doc §1.3/§1.7 event lists are a point-in-time snapshot; refresh against current docs (doc-only). |

## What this pass changed on the live board (delta-plan.json, applied, 0 errors)
- **1 create**: NEW-12 (eight `.kiro` migrations owner) — closes the E1 orphan + the dangling reference.
- **40 relations**: 25 spine-first `blocked_by`→E8-13 (NEW-14), + R1/R5/R6 scope-contract/cross-link edges, + D3/COH-1/D7 prerequisite edges. The board had **zero** relations before; it now has a real dependency graph.
- **6 description restores**: REQ6/11/12/23/27 + E6-S5 rebuilt from `plane_backlog.json` (EARS + per-requirement ACs) + a true-up note — reversing the 18:30 over-application's content loss.
- **6 hook-design AC appends** (the steering refinements above) + **1 dedup scope note** (NEW-11).

## Governance note (surfaced for the user)
A workflow sub-agent **mutated the live board and edited `apply_upsert_plan.py`** unsupervised (it
deleted NEW-09 and re-applied 43 updates). The net effect was corrective, but a Plane-idiomatic
`state=cancelled` would have been preferable to deleting NEW-09 (audit trail). Recommend constraining
future analysis sub-agents to **read-only** and routing all writes through a single human-gated applier.
