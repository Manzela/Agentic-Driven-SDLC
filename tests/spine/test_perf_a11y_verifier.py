"""Independent verifier for perf_a11y_verifier (REQ-VERIFY-007/008 / Property 31 / task 51).

These tests do NOT trust tools/perf_a11y_verifier.py — they exercise its public
contract directly and assert the documented behavior across the three fifth-layer
checks:

  PERF  (REQ-VERIFY-007 / 25.1):
    * a p95 measurement within budget passes.
    * a p95 measurement over budget fails with a recorded violation.

  A11Y  (REQ-VERIFY-008 / 25.2):
    * zero axe-core WCAG-A/AA violations passes.
    * one or more WCAG-A/AA violations fails.

  UI-SCREEN (REQ-VERIFY-008 Ubiquitous / Property 31):
    * a ui-screen item whose "error" state has no render evidence fails.
    * a complete ui-screen item (all four states with behavioral render
      evidence) passes.
"""

from __future__ import annotations

import os
import sys

# Make the repo's tools/ package importable regardless of pytest's rootdir.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from tools.perf_a11y_verifier import (
    verify_performance,
    verify_accessibility,
    verify_ui_screen,
)


# ---------------------------------------------------------------------------
# Performance — p95 within budget passes, over budget fails (REQ-VERIFY-007)
# ---------------------------------------------------------------------------

def test_perf_p95_within_budget_passes():
    result = verify_performance({"p95_ms": 180}, {"p95_ms": 200})
    assert result["passed"] is True
    assert result["violations"] == []


def test_perf_p95_at_budget_passes():
    # Budget is a ceiling: measured == budget must pass (<=, not <).
    result = verify_performance({"p95_ms": 200}, {"p95_ms": 200})
    assert result["passed"] is True
    assert result["violations"] == []


def test_perf_p95_over_budget_fails_with_violation():
    result = verify_performance({"p95_ms": 250}, {"p95_ms": 200})
    assert result["passed"] is False
    assert len(result["violations"]) >= 1
    v = result["violations"][0]
    assert v["metric"] == "p95_ms"
    assert v["measured"] == 250
    assert v["budget"] == 200


# ---------------------------------------------------------------------------
# Accessibility — zero violations passes, >0 fails (REQ-VERIFY-008)
# ---------------------------------------------------------------------------

def test_a11y_zero_violations_passes():
    result = verify_accessibility({"violations": []})
    assert result["passed"] is True
    assert result["violations"] == []


def test_a11y_wcag_aa_violation_fails():
    axe = {
        "violations": [
            {
                "id": "color-contrast",
                "impact": "serious",
                "tags": ["wcag2aa", "wcag143"],
                "nodes": [{"target": ["button"]}],
            }
        ]
    }
    result = verify_accessibility(axe)
    assert result["passed"] is False
    assert len(result["violations"]) >= 1
    assert result["violations"][0]["id"] == "color-contrast"


def test_a11y_wcag_a_violation_fails():
    axe = {
        "violations": [
            {"id": "image-alt", "impact": "critical", "tags": ["wcag2a", "wcag111"], "nodes": [{}]}
        ]
    }
    result = verify_accessibility(axe)
    assert result["passed"] is False
    assert len(result["violations"]) >= 1


# ---------------------------------------------------------------------------
# UI-screen — missing "error" render evidence fails, complete passes
# ---------------------------------------------------------------------------

_ALL_STATES = ("empty", "loading", "error", "ready")


def _ui_item(states_with_evidence):
    """A ui-screen item declaring all four states, with behavioral render
    evidence only for the states in ``states_with_evidence``."""
    return {
        "subtype": "ui-screen",
        "declared_states": list(_ALL_STATES),
        "evidence": [
            {"state": s, "evidence_kind": "behavioral"}
            for s in states_with_evidence
        ],
    }


def test_ui_screen_missing_error_render_evidence_fails():
    # Every state has render evidence EXCEPT "error".
    item = _ui_item([s for s in _ALL_STATES if s != "error"])
    result = verify_ui_screen(item)
    assert result["passed"] is False
    # The failure must be attributable to the "error" state's missing evidence.
    error_violations = [v for v in result["violations"] if v.get("state") == "error"]
    assert len(error_violations) >= 1
    assert error_violations[0]["kind"] == "missing_render_evidence"
    # Other states must remain satisfied.
    assert result["states"]["ready"] is True
    assert result["states"]["error"] is False


def test_ui_screen_complete_passes():
    item = _ui_item(_ALL_STATES)
    result = verify_ui_screen(item)
    assert result["passed"] is True
    assert result["violations"] == []
    assert all(result["states"][s] is True for s in _ALL_STATES)
