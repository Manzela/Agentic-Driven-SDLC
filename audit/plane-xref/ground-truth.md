# Ground truth — verified on-disk + live-board facts (branch spec-reconciliation, 2026-06-18)

This file is the shared, pre-verified substrate for the cross-reference fan-out. Every fact below
was confirmed this session against the working tree and the **live** Plane board (256 items). Do not
re-derive these; build on them. Cite a fact as `GT-n`.

## A. On-disk reality (matches the audit headline — the spine has NEVER fired)
- **GT-1** `.claude/settings.json` is **ABSENT**. No hook is registered with Claude Code. The
  designed six-hook spine has never run; the ralph-loop plugin `stop-hook.sh` owned the Stop event.
- **GT-2** `.claude/agents/` contains only `.gitkeep` — **no subagent base-prompts** exist on disk.
- **GT-3** Hooks present on disk: `.claude/hooks/{stop_hook.py, pre_tool_use_hook.py,
  subagent_stop_hook.py}`. **No** `session_start` or `post_tool_use` hook in `.claude/hooks/`
  (drafts exist only under `audit/steering-audit/proposed/05-…py` and `06-…py`).
- **GT-4** Root repo `CLAUDE.md` is **ABSENT** (a draft `09-CLAUDE.md` exists under proposed/).
- **GT-5** **Zero `*.sql` files** exist anywhere in-repo. The eight `.kiro` migrations 001-008 do
  not exist.
- **GT-6** `tools/` holds only: `actor_identity.py`, `evidence_collector.py`,
  `feature_list_check.py`, `structured_output.py`. **No `spec_validator.py`, no `execution_bounds`.**
- **GT-7** `tools/actor_identity.py` resolves `actor_agent` from `CLAUDE_AGENT_NAME`; the live hooks
  compare against the literal **`verifier.md`** (COH-1). No agent frontmatter carries that name yet
  (GT-2), so every proven-flip would block `actor_not_verifier` (fail-closed-but-stuck).
- **GT-8** Staged-but-UNAPPLIED remediation artifacts under `audit/steering-audit/proposed/`:
  `00-charter.md`, `01-settings.json`, `02-stop_hook-steering.md`, `03-pre_tool_use-steering.md`,
  `04-subagent_stop-steering.md`, `05-session_start_hook.py`, `06-post_tool_use_hook.py`,
  `07-agent-base-prompts.md`, `08-goal-directive.md`, `09-CLAUDE.md` / `09-CLAUDE-doctrine.md`.
  NONE are applied to live `.claude/`.
- **GT-9** `schema/feature_list.schema.json` already implements the four-field EvidenceRecord, the
  WIRING→integration allOf, and nfr_subtype/subtype/declared_states allOf (so E3-5/E4-S2/S4 schema
  work is verify-and-extend, not author-from-scratch).
- **GT-10** A globally-installed `ralph-loop` plugin exists and its `stop-hook.sh` is a no-op that
  re-injected the mega-prompt; the audit's C-LOOP-04 = 49× re-injection + 24 idle "standing by" turns.

## B. Live board facts (256 work-items)
- **GT-11** Hierarchy: 8 epics (E1-E8, also the 8 Modules) → 49 stories → 186 tasks (depth 2).
  Plus **13 audit-created roots** (`external_source=ascp-audit-reorg`, seq 251-263). 243 items are
  `ascp-kiro`. The 13 audit roots ARE correctly attached to a Module + a Phase cycle + a `phase:N`
  label (verified) — they are NOT orphaned.
- **GT-12** 12 workflow states: Backlog, Done, Agent-Triaged, Spec-Compiling, Spec-Verified,
  Plan-Approved, Agent-Executing, In-Verification, Human-Review, HANDOFF(cancelled),
  Blocked(cancelled), Failed(cancelled). State distribution: Backlog 190, Spec-Verified 29,
  Spec-Compiling 7, Plan-Approved 7, In-Verification 5, Agent-Executing 4, Agent-Triaged 9,
  Human-Review 3, Blocked 1, Done 1.
- **GT-13** 7 cycles = Phase 0 (Spine) … Phase 6. 8 Modules = E1…E8. 22 labels (phase:0-4,
  priority:{blocking,high,normal}, type:{wiring,nfr,functional}, gate:{security,completion,stop},
  agent:{research,tester,coder,initializer}, human:review, blocked/failed/handoff).
- **GT-14** external_id scheme: stories `story:ASCP-E8-13` / `story:E6-S2` / `story:REQ-INFRA-005`;
  tasks `task:ASCP-E8-13#0`; audit items `ascp-audit-reorg:NEW-01`. `external_source` is `ascp-kiro`
  or `ascp-audit-reorg`.

## C. Confirmed defects in the PRIOR reconciliation apply (the report claims these resolved; live board says otherwise)
- **GT-D1 — NEW-12 was never created as a standalone item.** The plan op "Author the eight .kiro
  migrations 001-008 + run_state completeness + gate_audit_log append-only grant" and the op
  "REQ-INFRA-005 — migration set provisioning (true-up AC#4)" BOTH resolved (by name/external_id) to
  the SAME live item `df8b5217` = `story:REQ-INFRA-005` (seq 20). The second PATCH overwrote the
  first. Live `REQ-INFRA-005` description now reads "…depend on NEW-12 authoring the migrations…" —
  **but NEW-12 does not exist on the board.** Report §5 / §3.2 claim 14 NEW items; only **13** were
  created (NEW-01..11,13,14, plus NEW-06/09 — but **no NEW-12**). E1's load-bearing migration
  authoring has **no owning item**; a dangling reference points at a non-existent NEW-12.
- **GT-D2 — NEW-14 blocked-by edges do NOT exist on the board.** E8-13 (`story:ASCP-E8-13`, live id
  `a120af4f`) has ALL relation buckets EMPTY (`blocked_by:[] blocking:[] relates_to:[]` …). The
  `apply_upsert_plan.py` tool only PATCHes description_html/state/labels + assigns module/cycle — it
  has **no relation-creation capability**. So NEW-14 exists as a *story describing* the edges, but the
  actual `blocked_by` relations from the ~24 hook-consuming stories to E8-13 (and the ralph-disable
  leg) were never created. The Plane relations endpoint that WORKS is
  `GET/POST /workspaces/{ws}/projects/{proj}/work-items/{id}/relations/` (returns the 8 buckets).
- **GT-D3 — apply collisions are a class, not a one-off.** Because the applier resolves ops by
  name→external_id and several plan ops share a target or a near-name, any two ops hitting the same
  live id mean the later silently clobbers the earlier (only description/state/labels are sent).
  Re-verify every claimed UPDATE actually landed its intended content on the live board.

## D. Tooling you may use (read-only is safe; writes only when synthesizing the delta)
- Board snapshot JSON: `audit/plane-xref/board-snapshot.json` (full, with desc_text).
- Board digest (readable): `audit/plane-xref/board-digest.md`.
- Live API: load `plane-integration/.env`, header `X-API-Key` + `CF-Access-Client-Id/Secret` +
  a non-default `User-Agent`. Base `PLANE_API_BASE`, project path
  `/workspaces/agentic-driven-sdlc/projects/0de2a9fb-…/`. Rate-limit ≥0.34s between calls.
  Endpoints: `/states/ /labels/ /modules/ /cycles/ /work-items/ /work-items/{id}/relations/
  /modules/{id}/module-issues/ /cycles/{id}/cycle-issues/`.
- Prior reconciliation: `docs/audits/spec-to-evidence-steering/plane-reconciliation-report.md`
  + machine plan `plane-upsert-plan.json` + applied log `plane-integration/.apply_log.json`.

## E. The audit source-of-truth (cross-reference TARGETS)
- `docs/audits/spec-to-evidence-steering/01-intent-model.md` — 6-hook lattice + REQ-* map.
- `…/02-findings.md` — current↔intent delta.
- `…/03-best-practices.md` — Tier-1 hook mechanics + prompt-engineering (official docs + issues).
- `…/04-transcript-forensics.md` — 18 verified findings (7 P0, 4 P1, 7 P2), 4 rejected.
- `…/05-remediation-spec.md` — coverage matrix, apply order, named prerequisites (A1-A9, D-prereqs).
- `…/06-verification-report.md` — red-team + convergence; final verdict.
