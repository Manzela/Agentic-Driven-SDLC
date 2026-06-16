"""Independent verifier test for S5-sessionstart (REQ-STATE-003/005, task 7.1).

Written by the verifier, NOT the implementer. Loads the hook's pure core and
asserts the three contract behaviors:

  1. A populated feature_list yields correct unproven_count / proven_count.
  2. feature_list=None yields a stub summary with counts == 0.
  3. resume_integrity_ok is False when durable_hash mismatches the recomputed
     hash, and True when it matches OR is omitted.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

# ── Load the hook module directly from .claude/hooks (not on sys.path) ───────

_HOOK_PATH = (
    Path(__file__).resolve().parents[2]
    / ".claude"
    / "hooks"
    / "session_start_hook.py"
)


def _load_hook():
    assert _HOOK_PATH.exists(), f"hook missing at {_HOOK_PATH}"
    spec = importlib.util.spec_from_file_location("session_start_hook_under_test", _HOOK_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


hook = _load_hook()


# ── 1. Populated feature_list → correct counts ───────────────────────────────

def test_populated_feature_list_counts_unproven_and_proven():
    feature_list = {
        "items": [
            {"id": "A", "status": "unproven"},
            {"id": "B", "status": "proven"},
            {"id": "C", "status": "unproven"},
            {"id": "D", "status": "proven"},
            {"id": "E", "status": "unproven"},
        ]
    }
    result = hook.session_start(
        feature_list=feature_list,
        progress="some progress text",
        git_status="",
    )
    assert result["unproven_count"] == 3, result
    assert result["proven_count"] == 2, result
    # Sanity: structured payload carries the named contract fields.
    assert "summary" in result
    assert result["resume_integrity_ok"] is True


def test_in_scope_false_items_are_excluded_from_counts():
    feature_list = {
        "items": [
            {"id": "A", "status": "unproven", "in_scope": True},
            {"id": "B", "status": "unproven", "in_scope": False},  # excluded
            {"id": "C", "status": "proven"},  # in_scope defaults True
            {"id": "D", "status": "proven", "in_scope": False},  # excluded
        ]
    }
    unproven, proven = hook._count_statuses(feature_list)
    assert unproven == 1, unproven
    assert proven == 1, proven


# ── 2. feature_list=None → zero-count stub ───────────────────────────────────

def test_none_feature_list_yields_zero_count_stub():
    result = hook.session_start(
        feature_list=None,
        progress=None,
        git_status=None,
    )
    assert result["unproven_count"] == 0, result
    assert result["proven_count"] == 0, result
    assert isinstance(result["summary"], str) and result["summary"], result
    # Non-blocking: a fresh session is never integrity-flagged.
    assert result["resume_integrity_ok"] is True


# ── 3. resume_integrity_ok: mismatch=False, match/omitted=True ────────────────

def test_resume_integrity_ok_false_on_hash_mismatch():
    git_status = " M file.py\n"
    progress = "step 4 of 9"
    wrong_hash = "sha256:" + "0" * 64
    result = hook.session_start(
        feature_list={"items": []},
        progress=progress,
        git_status=git_status,
        durable_hash=wrong_hash,
    )
    assert result["resume_integrity_ok"] is False, result


def test_resume_integrity_ok_true_on_hash_match():
    git_status = " M file.py\n"
    progress = "step 4 of 9"
    correct_hash = hook.compute_resume_hash(git_status, progress)
    result = hook.session_start(
        feature_list={"items": []},
        progress=progress,
        git_status=git_status,
        durable_hash=correct_hash,
    )
    assert result["resume_integrity_ok"] is True, result


def test_resume_integrity_ok_true_when_durable_hash_omitted():
    result = hook.session_start(
        feature_list={"items": []},
        progress="anything",
        git_status="anything",
        durable_hash=None,
    )
    assert result["resume_integrity_ok"] is True, result


def test_compute_resume_hash_is_deterministic_and_length_prefixed():
    # Length-prefix should prevent boundary collisions: ("a","bc") != ("ab","c").
    h1 = hook.compute_resume_hash("a", "bc")
    h2 = hook.compute_resume_hash("ab", "c")
    assert h1 != h2
    # Deterministic.
    assert hook.compute_resume_hash("x", "y") == hook.compute_resume_hash("x", "y")
    assert hook.compute_resume_hash("x", "y").startswith("sha256:")


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
