"""Independent verifier for spine slice S3-stophook.

REQ-GATE-002 / REQ-LOOP-005 / task 5.1. Mirrors Z3 CHECK-5b/5c/1/3.

These tests do NOT trust the implementer's docstrings. They exercise the
importable pure core (`evaluate_stop`) over plain dicts and assert the
decision contract:
    {"decision": "allow"|"block", "terminal": "COMPLETE"|"HANDOFF"|None, ...}

Load-bearing property under test (the infinite-block fix): HANDOFF triggers
(iteration cap / budget / no-progress) ALLOW termination even while in-scope
items remain unproven. They must NOT block — blocking there would force the
agent to loop past its cap forever.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

# ── Import the implementer's module by file path (no package assumption). ────
_HOOK_PATH = (
    Path(__file__).resolve().parents[2] / ".claude" / "hooks" / "stop_hook.py"
)
_spec = importlib.util.spec_from_file_location("stop_hook_under_test", _HOOK_PATH)
stop_hook = importlib.util.module_from_spec(_spec)
sys.modules["stop_hook_under_test"] = stop_hook
_spec.loader.exec_module(stop_hook)

evaluate_stop = stop_hook.evaluate_stop


# ── Fixture builders (the verifier owns these — independent of impl). ─────────

def _item(item_id, status="proven", in_scope=True):
    return {"id": item_id, "status": status, "in_scope": in_scope}


def _feature_list(items):
    return {"items": items}


def _run_state(**overrides):
    base = {
        "iteration_count": 0,
        "violation_count": 0,
        "budget_exceeded": False,
        "no_progress_n": 0,
    }
    base.update(overrides)
    return base


# ════════════════════════════════════════════════════════════════════════════
# (1) All in-scope items proven, no HANDOFF trigger -> allow / COMPLETE.
#     (Z3 CHECK-1: clean completion path.)
# ════════════════════════════════════════════════════════════════════════════

def test_all_proven_no_trigger_allows_complete():
    fl = _feature_list([
        _item("A", status="proven"),
        _item("B", status="proven"),
        # An out-of-scope unproven item must NOT affect the gate.
        _item("X", status="unproven", in_scope=False),
    ])
    decision = evaluate_stop(_run_state(), fl)
    assert decision["decision"] == "allow", decision
    assert decision["terminal"] == "COMPLETE", decision


# ════════════════════════════════════════════════════════════════════════════
# (2) One in-scope item unproven, no HANDOFF trigger -> block.
#     (Z3 CHECK-1: completion gate fails closed.)
# ════════════════════════════════════════════════════════════════════════════

def test_one_in_scope_unproven_blocks():
    fl = _feature_list([
        _item("A", status="proven"),
        _item("B", status="unproven"),
    ])
    decision = evaluate_stop(_run_state(), fl)
    assert decision["decision"] == "block", decision
    assert decision["terminal"] is None, decision


# ════════════════════════════════════════════════════════════════════════════
# (3) iteration_count == 25 with UNPROVEN items -> allow / HANDOFF (NOT block).
#     THE infinite-block fix. (Z3 CHECK-5b/5c.)
# ════════════════════════════════════════════════════════════════════════════

def test_iteration_cap_with_unproven_allows_handoff_not_block():
    fl = _feature_list([
        _item("A", status="proven"),
        _item("B", status="unproven"),  # deliberately unproven
        _item("C", status="failed"),
    ])
    decision = evaluate_stop(_run_state(iteration_count=25), fl)
    # The defect we are guarding against: blocking here.
    assert decision["decision"] == "allow", (
        "iteration cap with unproven items must ALLOW (HANDOFF), not block — "
        f"got {decision}"
    )
    assert decision["terminal"] == "HANDOFF", decision


# ════════════════════════════════════════════════════════════════════════════
# (4) no_progress streak >= 3 -> allow / HANDOFF.  (Z3 CHECK-3.)
# ════════════════════════════════════════════════════════════════════════════

def test_no_progress_streak_allows_handoff():
    fl = _feature_list([
        _item("A", status="proven"),
        _item("B", status="unproven"),
    ])
    decision = evaluate_stop(_run_state(no_progress_n=3), fl)
    assert decision["decision"] == "allow", decision
    assert decision["terminal"] == "HANDOFF", decision


def test_no_progress_below_threshold_does_not_handoff():
    # Streak of 2 must NOT trigger HANDOFF; with an unproven item it blocks.
    fl = _feature_list([
        _item("A", status="proven"),
        _item("B", status="unproven"),
    ])
    decision = evaluate_stop(_run_state(no_progress_n=2), fl)
    assert decision["decision"] == "block", decision
    assert decision["terminal"] is None, decision


# ════════════════════════════════════════════════════════════════════════════
# (5) budget_exceeded -> allow / HANDOFF.
# ════════════════════════════════════════════════════════════════════════════

def test_budget_exceeded_allows_handoff():
    fl = _feature_list([
        _item("A", status="unproven"),
    ])
    decision = evaluate_stop(_run_state(budget_exceeded=True), fl)
    assert decision["decision"] == "allow", decision
    assert decision["terminal"] == "HANDOFF", decision


# ════════════════════════════════════════════════════════════════════════════
# (6) violation_count == 2 -> block.  (Spec-completion violations remain.)
# ════════════════════════════════════════════════════════════════════════════

def test_positive_violation_count_blocks():
    fl = _feature_list([
        _item("A", status="proven"),  # everything proven; violations still block
    ])
    decision = evaluate_stop(_run_state(violation_count=2), fl)
    assert decision["decision"] == "block", decision
    assert decision["terminal"] is None, decision


# ════════════════════════════════════════════════════════════════════════════
# (7) violation_count == -1 -> block (fail-closed: validator error).
# ════════════════════════════════════════════════════════════════════════════

def test_negative_violation_count_fails_closed_blocks():
    fl = _feature_list([
        _item("A", status="proven"),
    ])
    decision = evaluate_stop(_run_state(violation_count=-1), fl)
    assert decision["decision"] == "block", decision
    assert decision["terminal"] is None, decision


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
