#!/usr/bin/env python3
"""Stop-hook decision logic for the spec-to-evidence control plane.

Implements REQ-GATE-002 / REQ-LOOP-005 (spine slice S3-stophook, task 5.1):
the `evaluate_stop` decision over plain dicts, plus the `check_no_progress`
watchdog. These are PURE, IMPORTABLE functions — no Claude-Code runtime, no
Postgres, no stdin. They take plain dicts (the run_state row and the
feature_list document) and return a plain decision dict. The Claude-Code Stop
hook entrypoint (`main`) reads JSON from stdin, calls `evaluate_stop`, and maps
the decision to an exit code; but the importable core has zero I/O so the
verifier can exercise it directly.

ORDER IS LOAD-BEARING (the infinite-block fix, design.md "No-Progress Watchdog"
~lines 952-1039): HANDOFF triggers (cap / budget / no-progress) are evaluated
FIRST and ALLOW termination (exit 0). At HANDOFF the in-scope items are EXPECTED
to remain unproven, so checking the unproven-items gate first and blocking would
force the agent to keep working past its cap — the infinite-block defect. Only
AFTER no HANDOFF trigger fires do the blocking gates (violation_count, unproven
in-scope items) apply. Any exception in the body fails CLOSED (returns block),
per REQ-GATE-005 ("ambiguous states SHALL resolve to blocked, not passed").
"""

from __future__ import annotations

import json
import os
import pathlib
import sys
from typing import Any

# Make `from tools...` resolve when run as a hook subprocess (cwd-independent).
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

# ── Module constants ────────────────────────────────────────────────────────
# Thresholds are env-overridable and single-sourced in tools/execution_bounds
# (no inline numeric literals here). An operator overrides them via the
# SPINE_* env vars; the importable core reads them at import time.
from tools.execution_bounds import (  # noqa: E402
    MAX_TURNS_PER_SLICE,
    N_PROGRESS_WINDOW,
    SPEC_COMPLETION_HARD_CAP,
    BLOCK_STREAK_HANDOFF,
)


# ── Decision constructors ───────────────────────────────────────────────────

def _allow(terminal: str | None, reason: str) -> dict:
    """ALLOW termination (exit 0). `terminal` is the terminal state reached:
    COMPLETE (all proven, no violations) or HANDOFF (a cap/budget/no-progress
    trigger fired)."""
    return {"decision": "allow", "terminal": terminal, "reason": reason}


def _block(reason: str) -> dict:
    """BLOCK termination (exit 2). No terminal state — the run must continue."""
    return {"decision": "block", "terminal": None, "reason": reason}


# ── No-progress watchdog (REQ-LOOP-002) ─────────────────────────────────────

def check_no_progress(run_state: dict) -> bool:
    """Return True iff the no-progress predicate has fired.

    No-progress (REQ-LOOP-002) is operationalized as a *streak counter*:
    `run_state["no_progress_n"]` is the number of consecutive no-progress slices
    observed so far (advanced by the loop driver when a slice produces neither a
    newly-proven item nor a commit, reset to 0 on any progress). The predicate
    FIRES only once the streak reaches the N_PROGRESS_WINDOW (=3) threshold.

    This function is a pure read of that counter — it does not mutate run_state
    and does not query slice history; the streak is maintained durably on the
    run_state row by the loop driver. A missing/None counter reads as 0 (no
    streak), so a fresh run is never spuriously flagged.
    """
    streak = run_state.get("no_progress_n", 0)
    if streak is None:
        streak = 0
    return int(streak) >= N_PROGRESS_WINDOW


# ── Stop decision (REQ-GATE-002 / REQ-LOOP-005) ─────────────────────────────

def evaluate_stop(run_state: dict, feature_list: dict) -> dict:
    """Decide whether an agent stop attempt is allowed or blocked.

    Returns {"decision": "allow"|"block",
             "terminal": "COMPLETE"|"HANDOFF"|None,
             "reason": str}.

    The entire body is wrapped so ANY exception fails CLOSED (returns block):
    an ambiguous/erroring evaluation must never read as a clean COMPLETE.
    """
    try:
        if run_state is None:
            return _block("Stop blocked: run_state is None. Fail closed.")
        if feature_list is None:
            return _block("Stop blocked: feature_list is None. Fail closed.")

        items = feature_list.get("items", [])
        # Gates count ONLY in-scope items (Reconciliation 2026-06-15).
        in_scope_items = [i for i in items if i.get("in_scope")]

        # ── HANDOFF triggers take precedence and ALLOW termination (exit 0).
        #    REQ-LOOP-005 / Requirement 21: iteration cap, cost budget, and
        #    no-progress route to HANDOFF and MUST NOT block. Evaluated BEFORE
        #    the unproven-items gate ON PURPOSE — at HANDOFF the in-scope items
        #    are EXPECTED to remain unproven, so blocking here would force the
        #    agent past its cap (the infinite-block defect; Z3 CHECK-5b/5c/8c).

        # (1) Iteration cap.
        iteration_count = run_state.get("iteration_count", 0) or 0
        if int(iteration_count) >= MAX_TURNS_PER_SLICE:
            return _allow(
                "HANDOFF",
                f"HANDOFF: iteration cap reached "
                f"(iteration_count={iteration_count} >= MAX_TURNS_PER_SLICE="
                f"{MAX_TURNS_PER_SLICE}). Escalate to a human (REQ-LOOP-005).",
            )

        # (2) Cost budget. budget_exceeded is a precomputed predicate on the
        #     run_state row (the loop driver computes token_cost_usd >=
        #     TOKEN_BUDGET). Truthy → HANDOFF.
        if run_state.get("budget_exceeded"):
            return _allow(
                "HANDOFF",
                "HANDOFF: token budget exceeded. Escalate to a human "
                "(REQ-LOOP-005).",
            )

        # (3) No-progress watchdog (N=3 consecutive no-progress slices).
        if check_no_progress(run_state):
            unproven = [
                i.get("id") for i in in_scope_items
                if i.get("status") != "proven"
            ]
            return _allow(
                "HANDOFF",
                f"HANDOFF: no progress over {N_PROGRESS_WINDOW} consecutive "
                f"slices (no items proven and no commits). Unproven: {unproven}. "
                f"Escalate to a human (REQ-LOOP-005).",
            )

        # (4) External blocker / repeated-block escalation. These ALSO route to
        #     HANDOFF (exit 0) so a stuck loop surfaces to a human instead of
        #     re-blocking forever. Placed AFTER the cap/budget/no-progress
        #     HANDOFF triggers and BEFORE the blocking gates (proposed/02).
        if str(run_state.get("external_blocker") or "").strip():
            return _allow(
                "HANDOFF",
                f"HANDOFF: external blocker declared: "
                f"{run_state['external_blocker']}. Hand to a human to clear it.",
            )
        if int(run_state.get("block_streak", 0) or 0) >= BLOCK_STREAK_HANDOFF:
            return _allow(
                "HANDOFF",
                f"HANDOFF: {run_state['block_streak']} consecutive blocked "
                f"stops (>= {BLOCK_STREAK_HANDOFF}). Escalating instead of "
                f"re-blocking.",
            )

        # ── Blocking gates (exit 2) — reached only when NO HANDOFF trigger is
        #    active. Here continuation is actually desired.

        # (a) Spec-completion violations (REQ-SPEC-021). A validator error
        #     (< 0) fails closed; outstanding violations (> 0) block.
        violation_count = run_state.get("violation_count", 0)
        if violation_count is None:
            return _block(
                "Stop blocked: violation_count is None (spec validator error). "
                "Fail closed."
            )
        if int(violation_count) < 0:
            return _block(
                "Stop blocked: spec validator error (violation_count < 0). "
                "Fail closed."
            )
        if int(violation_count) > 0:
            return _block(
                f"Stop blocked: {violation_count} spec-completion violation(s) "
                f"remain (REQ-SPEC-021)."
            )

        # (b) Empty-coverage-model gate. `items: []` (or no in-scope items) is a
        #     valid INIT state but NEVER a valid COMPLETE state — an all-empty
        #     model would trivially satisfy the completion gate below and read as
        #     COMPLETE before discovery has run. Require discovery first.
        if not in_scope_items:
            return _block(
                "Stop blocked: feature_list.json has zero in-scope items "
                "(items: []). This is a valid INIT state, not COMPLETE — run "
                "discovery before termination."
            )

        # (c) Completion gate. ANY in-scope item not EXACTLY 'proven' blocks
        #     (fail-closed; a 'failed' or 'unproven' item blocks identically).
        #     This is the ONLY legitimate exit-2 path where continuation is
        #     desired.
        not_proven = [i for i in in_scope_items if i.get("status") != "proven"]
        if not_proven:
            return _block(
                f"Stop blocked: {len(not_proven)} in-scope item(s) not proven: "
                f"{[i.get('id') for i in not_proven]}"
            )

        # All in-scope items proven, no violations, no HANDOFF trigger → COMPLETE.
        return _allow(
            "COMPLETE",
            f"COMPLETE: all {len(in_scope_items)} in-scope item(s) proven, no "
            f"outstanding violations, no HANDOFF trigger active.",
        )

    except Exception as exc:  # noqa: BLE001 — fail CLOSED on any error.
        return _block(
            f"Stop blocked: evaluate_stop raised {type(exc).__name__}: {exc}. "
            f"Fail closed."
        )


# ── Claude-Code Stop hook entrypoint ────────────────────────────────────────
# Thin I/O shell over the pure core. Reads the Stop event JSON from stdin
# (expects optional 'run_state' and 'feature_list' objects), evaluates, prints
# the decision dict, and maps decision → exit code (allow=0, block=2). All
# decision logic lives in evaluate_stop; this shell is intentionally trivial.
#
# SCOPE (interactive vs loop): the completeness gate is meaningful ONLY for the
# autonomous-loop Stop event, which the loop driver fires with a 'run_state'
# and/or 'feature_list' payload attached. A plain interactive Claude-Code Stop
# event carries neither key, so building an empty feature_list here would drive
# the gate into the empty-coverage branch ("zero in-scope items") and block
# every interactive turn-end on a valid INIT state that is neither reachable nor
# meaningful outside the loop. When neither key is present this is NOT a
# loop-gated stop → allow termination. The pure, formally-verified core
# (evaluate_stop) is unchanged and still gates fully whenever the loop supplies
# state — including a genuine INIT {"items": []} where the 'feature_list' key IS
# present and the empty-coverage block still fires.

def main(argv: list[str] | None = None) -> int:
    raw = sys.stdin.read()
    try:
        event: dict[str, Any] = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        # Unparseable event → fail closed. Block reason on STDERR (Claude Code
        # ignores stdout on exit 2).
        print("Stop blocked: unparseable Stop event JSON. Fail closed.",
              file=sys.stderr)
        return 2

    # Reentrancy: a forced continuation is NOT a fresh task. When the harness
    # re-fires Stop because the previous block injected a continuation,
    # `stop_hook_active` is set. Emit nothing, allow — re-gating here would loop.
    if event.get("stop_hook_active"):
        return 0

    # Load durable state from disk when the harness Stop event omits it. The
    # loop driver persists run_state.json/feature_list.json under
    # ${CLAUDE_PROJECT_DIR}; a real harness Stop event carries neither key.
    root = pathlib.Path(os.environ.get("CLAUDE_PROJECT_DIR", ".")).resolve()
    run_state = event.get("run_state")
    feature_list = event.get("feature_list")
    is_loop = ("run_state" in event) or ("feature_list" in event) or event.get("loop")
    # A corrupt durable-state file is an AMBIGUOUS state, not an absent one:
    # Stop is a CLOSED gate and MUST block (exit 2), never crash with exit 1
    # (which Claude Code treats as non-blocking, letting an incomplete loop
    # terminate silently). Mirror the unparseable-EVENT path above: catch the
    # decode/IO error, emit a block reason on STDERR, and fail CLOSED.
    # REQ-GATE-005: "ambiguous states SHALL resolve to blocked, not passed."
    if run_state is None:
        rs = root / "run_state.json"
        if rs.is_file():
            try:
                run_state = json.loads(rs.read_text())
            except (json.JSONDecodeError, OSError) as exc:
                print(
                    f"Stop blocked: run_state.json is unreadable "
                    f"({type(exc).__name__}: {exc}). Fail closed.",
                    file=sys.stderr,
                )
                return 2
    if feature_list is None:
        fl = root / "feature_list.json"
        if fl.is_file():
            try:
                feature_list = json.loads(fl.read_text())
            except (json.JSONDecodeError, OSError) as exc:
                print(
                    f"Stop blocked: feature_list.json is unreadable "
                    f"({type(exc).__name__}: {exc}). Fail closed.",
                    file=sys.stderr,
                )
                return 2

    # Interactive (non-loop) stop with no durable state: the completeness gate
    # does not apply — allow termination rather than block on empty coverage.
    if not is_loop and run_state is None and feature_list is None:
        return 0

    decision = evaluate_stop(run_state or {}, feature_list or {})
    if decision["decision"] == "allow":
        print(decision["reason"])
        return 0
    # Block reason on STDERR (Claude Code ignores stdout on exit 2).
    print(decision["reason"], file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
