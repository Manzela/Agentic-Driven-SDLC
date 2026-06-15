# Context

Fresh audit on 2026-05-17 reveals the repo state has moved substantially in the past 2 days. Most of Session A's and Session B's work has merged. **Only 4 PRs remain open, all `CONFLICTING/DIRTY`**, plus a structural problem: `main` and `phase/1` have **forked** — each contains valuable work the other lacks.

## Merge state snapshot

**Already merged (the win):**
- → `main`: PRs #6, #7, #8, #9, #10 (smoke), #11 (judge), #13 (toolsets), #14 (orchestrator), #15 (Session A anchors register), #17, #18, #25
- → `phase/1`: PRs #16 (gemini fix), #19, #20, #21, #22 (audit-plan note), #23 (integration test), #26 (Session A Task 1 polish)
- Plus the user's `0b0cb06` commit on `phase/1` (raise daily cap to 500 + hermes event catalog)

**The 4 stragglers (all `mergeable=CONFLICTING`):**
| PR | Owner | Target | Files | +Δ/-Δ | Real new work content |
|----|-------|--------|-------|-------|-----------------------|
| #12 | Session B | `main` | 97 | +19030/-8 | `lib/evaluators/consensus.py` + `tests/unit/test_consensus.py` (the actual NEW code is +193/-0; remaining 96 files are inherited stack pollution) |
| #24 | Session B | `main` | 96 | +18897/-8 | full `register()` replacing placeholder in `lib/evaluators/__init__.py` + `tests/unit/test_evaluators_plugin.py` (real NEW work is +138/-4; rest is stack pollution) |
| #27 | Session A | `phase/1` | 2 | +56/-12 | SpecStore docstring + test docstring polish (small, real) |
| #28 | Session A | `phase/1` | 2 | +103/-10 | clarification_loop honest tautology disclosure (small, real) |

## The fork problem

`main` is 21 commits ahead of `phase/1` and `phase/1` is 75 commits ahead of `main`. 30+ files differ between them. Critically:

| Asset | On `main`? | On `phase/1`? |
|-------|-----------|---------------|
| SDLC infra (`.github/`, `.gitleaks.toml`, `.markdownlint.jsonc`, dependabot, workflows) | ✅ YES | ❌ NO (deleted relative to main) |
| `lib/evaluators/{__init__,judge,orchestrator_hook}.py` | ✅ YES (placeholder __init__) | ❌ NO |
| Corrected `deploy/litellm/config.yaml` (gemini-3.1-pro-preview + global) | ❌ stale | ✅ YES |
| Session A's polished `lib/anchors/{task_spec,spec_store,intent_classifier,clarification_loop}.py` + tests | ❌ pre-polish | ✅ YES (4 polish PRs landed) |
| `lib/anchors/__init__.py` with full `register()` (Session A Task 5) | ✅ YES | ✅ YES (both — but possibly diverged content) |
| `audit/audit-plan.md` deviation note | ❌ NO | ✅ YES |
| `tests/integration/test_p1_2_judge_panel.py` | ❌ NO | ✅ YES |
| Updated `scripts/smoke.sh` (8 checks, gemini call) | ✅ YES (PR #10 landed) | ❌ NO (older 7-check version) |

Neither branch is a strict superset. **Both contain irreplaceable work** the user wants preserved.

---

# Recommended approach — 3-phase merge plan

The plan converges both branches and lands the 4 remaining PRs without losing any work. It splits responsibilities cleanly: Session B fixes Session B's PRs; Session A fixes Session A's PRs; main↔phase/1 reconciliation is the joint project-level step.

## Phase 1 — Session B lands PRs #12 and #24 (Session B's scope)

Both branches inherit stale stacked content from earlier PRs (#11 for #12, #14 for #24) that has since merged separately. The fix is the same per branch: reset to current `origin/main` and re-apply only the NEW work.

### PR #12 — `lib/evaluators/consensus.py`

1. Read the consensus.py content from `origin/session-b/p1-2-task-17-consensus:lib/evaluators/consensus.py` and the test file (already verified intact: 126 + 67 lines).
2. Create a fresh branch from `origin/main`:
   `git checkout -b session-b/p1-2-task-17-consensus-on-main origin/main`
3. Stage just the two NEW files (`lib/evaluators/consensus.py` + `tests/unit/test_consensus.py`) by file-copy from the old branch's tree.
4. Verify tests pass against current `main` (`pytest tests/unit/test_consensus.py` should give 8/8).
5. Commit with message body identical to the original (preserve Session-B attribution).
6. Either: (a) **force-push to the existing branch** `session-b/p1-2-task-17-consensus` and retarget PR #12 with `gh pr edit 12 --base main`, OR (b) **close PR #12 + push the new branch + open a fresh PR** referencing #12 in the description.
   - **(a) is preferred** because it preserves PR #12's history/reviews/comments. Force-push uses `--force-with-lease`.

### PR #24 — full `register()` in `lib/evaluators/__init__.py`

Same pattern. The real new content is:
- `lib/evaluators/__init__.py` — replace the placeholder docstring with the full `register(ctx)` that wires `post_tool_call`, `pre_llm_call`, `on_session_end`.
- `tests/unit/test_evaluators_plugin.py` — 6 tests.

Steps mirror PR #12. Verify with `pytest tests/unit/test_evaluators_plugin.py` (6 PASS) plus `tests/unit/test_orchestrator_hook.py` (3 PASS) to confirm the package imports still work.

### Critical: do NOT delete inherited files

When force-pushing the rebased branches, ensure judge.py and orchestrator_hook.py are NOT in the commit (they're already on main). Use `git diff origin/main..HEAD` to confirm the diff shows ONLY the intended new files before pushing.

## Phase 2 — Session A lands PRs #27 and #28 (Session A's scope — NOT Session B's responsibility)

Coord-file handoff: Session B will not touch these. The same pattern applies (rebase onto current `origin/phase/1`, cherry-pick the polish-2 commit, force-push). Session A will likely identify and execute this independently. Session B's coord-file update flags them as Session A's work.

## Phase 3 — Reconcile `main` ↔ `phase/1` (project-level, jointly executed)

After Phase 1 lands, `main` has all Session B P1-2 code. After Phase 2 lands, `phase/1` has all Session A polish.

**Recommendation: merge `phase/1` → `main` via a single reconciliation PR.** Rationale: `phase/1` has more content (75 commits vs 21), and the SDLC infra on main is additive (no conflict with phase/1's content). A merge brings:
- Session A's anchors polish (replaces main's pre-polish anchors files)
- Session B's gemini-3.1-pro-preview corrections (replaces main's stale model_name)
- Session B's audit-plan note + integration test (additive — no conflict)
- The user's daily cap raise + hermes event catalog (additive)

Expected conflicts (~16 files per the `git merge --no-commit` dry-run we did): all in `lib/anchors/`, `config/limits.yaml`, `config/toolsets.yaml`, `audit/audit-plan.md`, `deploy/litellm/config.yaml`. **For each, keep `phase/1`'s version** (more recent + polished). The CI/SDLC infra files (`.github/*`, `.gitleaks.toml`, etc.) are unique to main and will merge clean (no conflict).

This phase is BLOCKING on Phase 1 + Phase 2 — defer until both are done.

---

## Critical files

- `/Users/danielmanzela/RX-Research Project/AutonomousAgent/.worktrees/session-b-task-17` (branch for PR #12)
- `/Users/danielmanzela/RX-Research Project/AutonomousAgent/.worktrees/session-b-task-20a` (branch for PR #24)
- `/Users/danielmanzela/RX-Research Project/AutonomousAgent/.worktrees/phase1/docs/superpowers/session-coordination.md` (coord-file update before any force-push)
- The content to preserve, sourced from origin (NOT from local stale worktrees, which may have drifted):
  - `origin/session-b/p1-2-task-17-consensus:lib/evaluators/consensus.py`
  - `origin/session-b/p1-2-task-17-consensus:tests/unit/test_consensus.py`
  - `origin/session-b/p1-2-task-20a-plugin-register:lib/evaluators/__init__.py`
  - `origin/session-b/p1-2-task-20a-plugin-register:tests/unit/test_evaluators_plugin.py`

## Safety guarantees

- **No deletion of existing work.** Every PR's actual content is preserved (verified by `git show origin/<branch>:<file>` before any reset).
- **No silent overwrite of Session A.** Phase 1 only force-pushes `session-b/*` branches. Phase 2 is Session A's; the coord file announces Session B's intent before any push so Session A sees the boundary.
- **No `phase/1` mutation in Phase 1.** Reconciliation happens only in Phase 3 (project-level, after both sessions ack).
- **`--force-with-lease`** on every force-push to prevent stomping concurrent updates from origin.
- **Stale-data check.** Read every preserved file directly from `origin/...` after `git fetch`, never from a possibly-stale local worktree.

## Verification (per phase)

### Phase 1 verification
- `gh pr view 12 --json mergeable,changedFiles,additions,deletions` → MERGEABLE, 2 files, ~+193/-0
- `gh pr view 24 --json mergeable,changedFiles,additions,deletions` → MERGEABLE, 2 files, ~+138/-4
- Live unit-test re-run: `pytest tests/unit/test_consensus.py tests/unit/test_evaluators_plugin.py tests/unit/test_orchestrator_hook.py tests/unit/test_judge.py` → 22/22 PASS
- Live integration test (against the running LiteLLM stack which serves Gemini): `pytest tests/integration/test_p1_2_judge_panel.py -v` → 1 PASS

### Phase 2 verification (Session A's responsibility)
- `gh pr view 27 --json mergeable` and `gh pr view 28 --json mergeable` → MERGEABLE with small diffs

### Phase 3 verification (project-level)
- `git diff --name-only origin/main origin/phase/1` → 0 files (post-merge)
- `pytest tests/ -q` on `phase/1` (now merged with main) → all green
- `bash scripts/smoke.sh` → 8/8 PASS end-to-end

## What is explicitly NOT in this plan

- **No close-and-recreate of PRs #12 or #24.** Force-push preserves history/reviews.
- **No touching of Session A's PRs #27 and #28.** Session A's domain.
- **No `main` rewrite.** `main` is the deployed branch; only additive merges allowed.
- **No deletion of any file on either branch during Phase 1 or Phase 2.** Only Phase 3's merge resolves divergent content (always by accepting `phase/1`'s polished versions where they differ).
