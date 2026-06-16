"""Independent verifier for state_integrity (REQ-STATE-005 / Property 26 / task 49).

These tests do NOT trust the internals of tools/state_integrity.py — they
exercise its public contract (compute_state_hash, check_resume_integrity)
directly and assert the documented Property-26 behavior:

  * compute_state_hash is deterministic: identical inputs -> identical digest.
  * the digest is a 64-char lowercase hex sha256 string.
  * determinism is logical, not textual: insertion order / dependency-list
    order / whitespace must not perturb the digest.
  * check_resume_integrity is True when stored == recomputed (faithful resume).
  * check_resume_integrity is False when ANY hashed input changed (tamper) —
    tested across feature-list, run_state, and git_status mutations.
  * a missing/empty stored baseline is not treated as a match (returns False).
"""

from __future__ import annotations

import os
import re
import sys

# Make the repo's tools/ package importable regardless of pytest's rootdir.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from tools.state_integrity import check_resume_integrity, compute_state_hash

_HEX64 = re.compile(r"\A[0-9a-f]{64}\Z")


def _git_status():
    return "## main...origin/main\n M tools/state_integrity.py"


def _progress():
    """A durable run_state mirror as the JSON string SessionStart loads."""
    return (
        '{"phase":"build","current_item_id":"item-2","iteration_count":4,'
        '"violation_count":1,"last_commit_sha":"deadbeef",'
        '"updated_at":"2026-06-16T00:00:00Z","token_cost_usd":1.23,'
        '"stop_hook_active":true}'
    )


def _feature_list():
    return {
        "items": [
            {
                "id": "item-1",
                "type": "feature",
                "priority": 1,
                "dependencies": ["dep-b", "dep-a"],
                "acceptance_criteria": "AC-1",
                "in_scope": True,
                "status": "done",
            },
            {
                "id": "item-2",
                "type": "feature",
                "priority": 2,
                "dependencies": [],
                "acceptance_criteria": "AC-2",
                "in_scope": True,
                "status": "in_progress",
            },
            {
                # Out-of-scope item must not participate in the hash.
                "id": "item-3",
                "type": "feature",
                "priority": 3,
                "dependencies": [],
                "acceptance_criteria": "AC-3",
                "in_scope": False,
                "status": "todo",
            },
        ]
    }


# ---------------------------------------------------------------------------
# compute_state_hash: determinism + shape
# ---------------------------------------------------------------------------


def test_compute_state_hash_is_deterministic():
    """Same inputs -> same hash, across repeated calls."""
    gs, prog, fl = _git_status(), _progress(), _feature_list()
    h1 = compute_state_hash(gs, prog, fl)
    h2 = compute_state_hash(gs, prog, fl)
    assert h1 == h2


def test_hash_is_64_hex():
    """The digest is a 64-char lowercase hex sha256 string."""
    h = compute_state_hash(_git_status(), _progress(), _feature_list())
    assert isinstance(h, str)
    assert len(h) == 64
    assert _HEX64.match(h) is not None


def test_determinism_is_logical_not_textual():
    """Item insertion order and dependency-list order must not change the digest."""
    gs, prog = _git_status(), _progress()
    fl = _feature_list()

    # Reverse the item order and the dependency list order of a deep copy.
    shuffled = {"items": list(reversed([dict(it) for it in fl["items"]]))}
    for it in shuffled["items"]:
        it["dependencies"] = list(reversed(it["dependencies"]))

    assert compute_state_hash(gs, prog, fl) == compute_state_hash(gs, prog, shuffled)


# ---------------------------------------------------------------------------
# check_resume_integrity: True when stored == recomputed
# ---------------------------------------------------------------------------


def test_check_resume_integrity_true_when_match():
    """Stored baseline equal to a fresh recomputation -> True (faithful resume)."""
    gs, prog, fl = _git_status(), _progress(), _feature_list()
    stored = compute_state_hash(gs, prog, fl)
    assert check_resume_integrity(stored, gs, prog, fl) is True


# ---------------------------------------------------------------------------
# check_resume_integrity: False on tamper of ANY hashed input
# ---------------------------------------------------------------------------


def test_tamper_feature_list_status_fails():
    gs, prog, fl = _git_status(), _progress(), _feature_list()
    stored = compute_state_hash(gs, prog, fl)

    tampered = _feature_list()
    tampered["items"][1]["status"] = "done"  # was "in_progress"
    assert check_resume_integrity(stored, gs, prog, tampered) is False


def test_tamper_feature_list_priority_fails():
    gs, prog, fl = _git_status(), _progress(), _feature_list()
    stored = compute_state_hash(gs, prog, fl)

    tampered = _feature_list()
    tampered["items"][0]["priority"] = 99
    assert check_resume_integrity(stored, gs, prog, tampered) is False


def test_tamper_run_state_fails():
    gs, prog, fl = _git_status(), _progress(), _feature_list()
    stored = compute_state_hash(gs, prog, fl)

    tampered_prog = prog.replace('"iteration_count":4', '"iteration_count":5')
    assert tampered_prog != prog
    assert check_resume_integrity(stored, gs, tampered_prog, fl) is False


def test_tamper_git_status_fails():
    gs, prog, fl = _git_status(), _progress(), _feature_list()
    stored = compute_state_hash(gs, prog, fl)

    assert check_resume_integrity(stored, gs + "\n M extra.py", prog, fl) is False


def test_volatile_run_state_fields_do_not_affect_hash():
    """updated_at / token_cost_usd / stop_hook_active are excluded from the hash."""
    gs, fl = _git_status(), _feature_list()
    base = compute_state_hash(gs, _progress(), fl)

    volatile_changed = (
        '{"phase":"build","current_item_id":"item-2","iteration_count":4,'
        '"violation_count":1,"last_commit_sha":"deadbeef",'
        '"updated_at":"2099-12-31T23:59:59Z","token_cost_usd":999.99,'
        '"stop_hook_active":false}'
    )
    assert compute_state_hash(gs, volatile_changed, fl) == base


def test_empty_stored_baseline_is_not_a_match():
    """A missing/empty baseline must not be reported as integrity-ok."""
    gs, prog, fl = _git_status(), _progress(), _feature_list()
    assert check_resume_integrity("", gs, prog, fl) is False
    assert check_resume_integrity(None, gs, prog, fl) is False
