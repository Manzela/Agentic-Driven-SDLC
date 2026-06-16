-- 005_run_state.sql
-- run_state: per-session execution state for resumption
-- Source: .kiro/specs/spec-to-evidence-control/design.md (Postgres Schema)
-- Phase 2 (durable state). Faithful to the canonical CREATE TABLE block.
-- Carries: status CHECK + stop_hook_active + no_progress_n + resume_integrity_ok
--          + violation_count + retry_count (+ prev_violation_count, spec_pass_count,
--          is_resume, first_write_done, resume_state_hash per reconciliation).

CREATE TABLE run_state (
    session_id        TEXT PRIMARY KEY,
    project_id        TEXT NOT NULL,
    current_item_id   TEXT REFERENCES requirements(id),
    status            TEXT NOT NULL CHECK (status IN
                        ('running', 'complete', 'handoff', 'blocked')),
    phase             TEXT NOT NULL DEFAULT 'spec' CHECK (phase IN ('spec', 'implementation')),
                      -- Reconciliation 2026-06-16: discriminates the two loops the Stop hook serves.
                      -- 'spec' (Req 4): SPEC_COMPLETION_HARD_CAP=7 passes + pass-level strict-decrease no-progress.
                      -- 'implementation' (Req 10/14): MAX_TURNS_PER_SLICE=25 + slice-level N=3 check_no_progress.
                      -- The two loops have different caps and different no-progress semantics; evaluate_stop branches on this.
    iteration_count   INTEGER NOT NULL DEFAULT 0,  -- the 25-turn MAX_TURNS_PER_SLICE counter (implementation phase); NOT the spec-pass counter
    spec_pass_count   INTEGER NOT NULL DEFAULT 0,  -- Reconciliation 2026-06-16: the spec-phase elaboration-pass counter, capped at SPEC_COMPLETION_HARD_CAP=7; DISTINCT from iteration_count (the 25-turn slice counter). The lex-specialis HANDOFF tiebreak keys on spec_pass_count >= SPEC_COMPLETION_HARD_CAP, NOT on iteration_count (added by task 28.5)
    token_cost_usd    NUMERIC(10,4) NOT NULL DEFAULT 0,  -- Reconciliation 2026-06-16: the budget THRESHOLD is the config constant TOKEN_BUDGET (task 44 / Req 20), NOT a column; the Stop hook computes budget_exceeded := token_cost_usd >= TOKEN_BUDGET. There is intentionally no token_budget_usd / budget_exceeded column.
    no_progress_n     INTEGER NOT NULL DEFAULT 0,  -- consecutive no-progress slices
    violation_count   INTEGER NOT NULL DEFAULT 0,  -- Reconciliation 2026-06-15: outstanding spec-completion violations; the Stop hook (evaluate_stop) reads this and blocks termination while > 0
    prev_violation_count INTEGER,                  -- Reconciliation 2026-06-16: the PRIOR spec-completion pass's violation_count; the Initializer loop compares current vs prev to enforce Property 15 strict-decrease-or-HANDOFF (Req 4.3). NULL before the first pass; added by migration 005_run_state.sql (task 28.5)
    retry_count       INTEGER NOT NULL DEFAULT 0,  -- Reconciliation 2026-06-15: implementer-loop retry budget counter (DEFAULT cap 3/slice)
    resume_integrity_ok BOOLEAN,                   -- Reconciliation 2026-06-15: written by SessionStart via state_integrity.py; PreToolUse integrity guard blocks the first write when FALSE (REQ-STATE-005).
                       -- Reconciliation 2026-06-16: FIRST-RUN / NO-BASELINE behavior (plain BOOLEAN, no SQL DEFAULT, so a fresh session has no recorded baseline and the comparison is undefined). On a session with NO prior durable resume_state_hash, state_integrity.py sets resume_integrity_ok=TRUE (and the PreToolUse integrity guard treats a NULL/absent baseline as ALLOW), so ONLY an actual recorded-vs-recomputed MISMATCH blocks — a fresh, non-resumed run is NEVER blocked by the integrity guard (asserted by task 39.16).
    is_resume         BOOLEAN NOT NULL DEFAULT FALSE, -- Reconciliation 2026-06-16: set TRUE by SessionStart when a prior run_state row for this session already exists (the session is a RESUME, not a fresh start). The PreToolUse integrity guard is scoped to (is_resume AND NOT first_write_done) so it fires ONLY on the first implementation write of a RESUMED session (Property 26 / Req 23.2 scope).
    first_write_done  BOOLEAN NOT NULL DEFAULT FALSE, -- Reconciliation 2026-06-16: set TRUE after the integrity guard passes the first Write/Edit of a resumed session, so the guard does not re-fire on every subsequent write. (is_resume AND NOT first_write_done) is the exact "first write of a resumed session" predicate the guard keys on (task 49.1).
    resume_state_hash TEXT,                        -- Reconciliation 2026-06-16: the durable BASELINE resumed-state hash that state_integrity.py compares its SessionStart recomputation against (requirements.md:437 "the durable store's recorded hash" had no column to live in). sha256 over the canonical projection of in-scope feature_list.json items + named run_state fields (full spec at Property 26). PRODUCER: written by the PreCompact hook checkpoint AND by each per-Slice commit (the moments the durable state is known-good); SessionStart RECOMPUTES and compares, equality -> resume_integrity_ok=true, mismatch -> false. NULL = no recorded baseline yet (fresh/non-resumed session). Added by state_integrity.py's migration / migration 005_run_state.sql (task 28.5).
    stop_hook_active  BOOLEAN NOT NULL DEFAULT FALSE,
    last_commit_sha   TEXT,
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
