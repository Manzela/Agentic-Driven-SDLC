# Plane board ⇄ steering-audit cross-reference — verification & optimization report

> Deepening pass on branch `spec-reconciliation`, 2026-06-18. Cross-references the live Plane board
> (`agentic-driven-sdlc/…/0de2a9fb…`, 256 work-items) against the six steering-audit deliverables
> (`docs/audits/spec-to-evidence-steering/01-06`) and the prior reconciliation, then lands the gaps.
> Companion: [`findings-register.md`](./findings-register.md) · [`delta-plan.json`](./delta-plan.json) ·
> [`board-snapshot.json`](./board-snapshot.json) (final) · `board-snapshot-1748.json` (baseline).

## 0. Headline

The prior reconciliation's **plan** was sound; its **delivery to the board was not**. The applier
silently dropped acceptance-criteria, priority, and multi-target batch ops, and structurally could not
create relations or a colliding new item. So the report read "execution-ready" while the board carried
narrative blurbs without testable ACs, no dependency edges, a missing migration owner, and stale states.
A mid-run sub-agent fixed the field-drops (ACs/priority/states) but introduced content loss and a stray
deletion. **This pass closed the structural remainder** — created the missing owner, built the entire
dependency graph (40 edges; the board had zero), restored the clobbered descriptions, and encoded the
hook-correctness/generalization fixes as testable ACs. The board is now internally coherent and
dependency-ordered. **It is not yet *executable in fact*, because the audit's actual code remediation
(register the spine) has still never been applied to `.claude/` — that remains the gating real-world work.**

## 1. What was wrong, and the class of error

| Class | What | Why it mattered | Resolution |
|---|---|---|---|
| **Applier field-drop** | `acceptance_criteria` / `priority` / `additional_match_keys` never sent | items had no checkable "done"; triage broke; 6/7 true-ups missed | folded + re-applied (mid-run); verified live |
| **Create-collision** | NEW-12 shared a match_key with REQ-INFRA-005 → overwritten | E1 migration work had **no owning item**; a dangling "depends on NEW-12" | created standalone (seq 264) |
| **Relation vacuum** | applier cannot POST relations; NEW-14 was prose-only | the spine-first ordering the whole plan relies on **did not exist** | **40 real edges** created |
| **Content loss** | batch true-up over-wrote 6 stories with one generic note | executors would see a stub, not the requirement | restored from `plane_backlog.json` |
| **Hook-design defects** | stdout-not-stderr; matcher misses Bash; spoofable actor; invalid decision value; brittle literal | the steering would *not actually steer* — root of self-correction loops | encoded as testable ACs (§3) |

## 2. The board now (verified live, post-apply)

- **256 work-items** — 8 epics → 49 stories → 186 tasks + **13 audit-owned items** (NEW-01…14 minus
  the de-duplicated NEW-09). Every audit item carries an epic (module), a phase cycle, and a `phase:*`
  label. **0 orphans.**
- **Dependency graph exists for the first time:** E8-13 (settings.json / A1) has **25 `blocking`**
  edges; every hook-consuming story is `blocked_by` it. Prerequisite edges bind D3/NEW-02,
  COH-1/NEW-05, D7/NEW-11 to their consumers; scope-contract edges (R1/R5/R6) bind the overlapping
  owners. So Roadmap/Active-Sprint dependency ordering is now enforceable, not assumed.
- **States reconciled:** **0 dead-end Blocked**, no Done-without-evidence, no human-owned item left
  Agent-Executing. (Residual advanced-state items flagged in §5.)
- **NEW-12** present (E1 / Phase 0 / `priority:blocking`).

## 3. Steering & hook optimizations (the autonomous-loop core) — now testable ACs on the board

These are the "minor semantic" places where the hooks/base-prompts were **not general or dynamic
enough**, which is precisely what makes the Claude-Code agent fight/patch the hook instead of being
steered. Each is now a checkable acceptance criterion on the owning item.

1. **Exit-2 reason → STDERR, never stdout** (E8-13). On a PreToolUse/Stop *block*, Claude Code feeds
   **stderr** back to the model; stdout shows only to the user. A hook that prints its steer to stdout
   then `exit 2` makes the steer invisible → the agent retries blindly and loops. *This single bug
   plausibly underlies a large share of the "agent corrects the hook" behavior.*
2. **PreToolUse matcher must include `Bash` + a content-level path check** (E8-13). A
   `Write|Edit|MultiEdit`-only matcher is bypassed by `sed -i`/`tee`/`echo >`/`python -c`, so the
   protected-path anti-tamper never fires for the most common evasion. Match on *what the command
   touches*, not just the tool name.
3. **Reentrancy on the runtime's `stop_hook_active` payload flag**, not a self-authored mutex
   (E5-S10/E8-14). The designed `run_state.stop_hook_active` is unwritten until D3 and races the very
   loop it guards; Claude Code already supplies the flag in the hook input — use it. Pair with the
   **CH-10 escalate-don't-re-inject** rung (a Stop re-entry emits **zero tokens**; N-streak → HANDOFF).
   This is the direct, testable fix for the forensics' 49× re-injection + 24 idle "standing-by" turns.
4. **Resolve actor server-side from `CLAUDE_AGENT_NAME`, not a payload field** (E4-S1). Trusting a
   payload `actor_agent` lets the gated subagent spoof the verifier identity, defeating
   actor-independence. And the SubagentStop `decision` must be a valid value (`block`/omit) — `approve`
   is silently ignored, so a self-graded record passes.
5. **Generalize the `verifier.md` literal behind one `VERIFIER_ROLE` constant/env** (NEW-05). A
   byte-for-byte literal duplicated across hooks + fixtures drifts on any rename and re-creates the
   fail-closed-but-stuck failure. One constant = one-line rename.
6. **Fail-open with a diagnostic** remains the rule for every hook (a hook *bug* must not hard-block the
   loop) — preserved and reaffirmed across the canary (NEW-01) and the forcing-function (NEW-10).

**Pattern behind all six:** steer with *categories, registries, env-scoped constants, and the runtime's
own signals* — not hard-coded paths, exact tool-name lists, byte-literals, or self-authored state that
races the loop. Reason-strings must always carry **the located oracle + one corrective next step**, on
**stderr**, so the agent is *redirected* rather than left to invent a fix (which is the loop).

## 4. View-readiness (the 8 board views), after this pass

| View | Status | Note |
|---|---|---|
| 🎯 Active Sprint (Phase 0) | **Ready (ordered)** | Phase 0 has every owning item incl. NEW-12; 25 `blocked_by`→E8-13 edges enforce spine-first order. |
| 🗺️ Roadmap (Gantt by phase) | **Ready** | All 13 audit items phase-placed; dependency edges drive the Gantt; no phase-orphan. |
| 🚦 Workflow Kanban | **Ready** | 0 dead-end Blocked; states reconciled; advanced states flagged in §5. |
| 📍 By Phase | **Ready** | every item has a `phase:*` label + cycle. |
| 🏛️ By Epic | **Ready** | every epic has its owning items; NEW-12 closes E1. |
| 🔥 Priority Triage | **Ready** | priority set across all items (urgent/high/medium); blocking set = the spine critical path. |
| 🤖 By Agent / Ownership | **Ready-pending-COH-1** | `agent:*` ↔ `<role>.md` reconciliation owned by NEW-05 (edges added); resolves when NEW-05 lands. |
| 📥 Backlog | **Ready** | deferred-but-tracked tail (NEW-07 D10/D11) lives here cleanly. |

## 5. Residual / verify-before-trust (not closed, with rationale)

- **Advanced-state stories beyond the E7 set** (E8-15/E8-19/E5-S17/S30/S32/E6-S6, per COV-04/WF-05):
  *not* blanket-true-upped, because some load-bearing artifacts **do** exist on disk (the three hooks,
  `actor_identity`, `evidence_collector`, `feature_list_check`, the schema), so a blanket Backlog move
  could be wrong. Each needs a per-item on-disk evidence check before its state is trusted.
- **Phase-label↔AC nits** (E6-S6 phase, E8-19 phase:3-vs-Phase-6) — low-value field edits, deferred.
- **best-practices doc refresh** (BP-5) and **per-op apply logging** (AI-06) — doc/tooling hygiene.
- **The real gate:** none of the `.claude/` remediation (settings.json, base-prompts, the new hooks) is
  applied to disk. The board is now a faithful, ordered plan *for* that work; executing it is the next
  real-world step (begin at Milestone 0 / COH-1, then E8-13).

## 6. Tooling left in place (durable)
- `plane-integration/apply_delta.py` — relation edges + MD/HTML + append-mode + module/cycle assignment
  (what `apply_upsert_plan.py` couldn't do); dry-run default, idempotent, no deletions.
- `plane-integration/dump_board.py` — full read-only board snapshot.
- `plane-integration/build_delta.py` — regenerates this pass's delta from verified state.
- Apply log: `plane-integration/.apply_delta_log.json` (per-op outcomes).
