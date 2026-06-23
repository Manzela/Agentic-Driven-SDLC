"""Diff-aware orphan detection (Task 3 §3.3-3.7).

Verifies detect_orphans_diff: forward scoped to changed files (minus the tools/
allowlist regex), backward scoped to feature_list.json model-deltas (never
path-exempt), dangling-ref subclass, CI fail-closed on an unreachable merge-base,
and the local full-repo fallback. The git helpers are exercised via subprocess mocks.

NOTE (2026-06-23): the plan's Task-3 tests were rewritten here — they passed
`baseline_has_file=` (no such param), empty `known_ids` (skips the cross-check),
a `tools/**` glob (the allowlist is a `tools/.*` regex), and an invalid `WIRING-001`
id (minted ids are `REQ-WIRE-NNN`). These fixtures use correct values.
"""
from unittest.mock import MagicMock, patch

from tools.orphan_detector import (
    _filter_forward_units_by_changed,
    _get_changed_files,
    _get_merged_base,
    _load_feature_list_from_commit,
    detect_orphans_diff,
)


# --- forward pass: changed-files scoping + tools/ allowlist -------------------
def test_forward_orphan_in_changed_file_is_flagged():
    result = detect_orphans_diff(
        impl_units=[{"file": "new_module.py", "text": "def foo(): pass"}],
        requirements=[],
        known_ids={"REQ-TEST-001"},
        changed_files={"new_module.py"},
    )
    assert "new_module.py" in str(result["forward_orphans"])
    assert result["ok"] is False


def test_forward_orphan_in_tools_is_exempt():
    result = detect_orphans_diff(
        impl_units=[{"file": "tools/helper.py", "text": "# helper, no REQ"}],
        requirements=[],
        known_ids={"REQ-TEST-001"},
        changed_files={"tools/helper.py"},
        allowlist_pattern="tools/.*",
    )
    assert "tools/helper.py" not in str(result["forward_orphans"])
    assert result["ok"] is True


def test_unit_in_unchanged_file_is_not_scanned():
    result = detect_orphans_diff(
        impl_units=[{"file": "untouched.py", "text": "no req"}],
        requirements=[],
        known_ids={"REQ-TEST-001"},
        changed_files={"other.py"},  # untouched.py is NOT changed
    )
    assert result["forward_orphans"] == []
    assert result["ok"] is True


# --- backward pass: model-delta scoping (never path-exempt) -------------------
def test_backward_orphan_from_model_delta_only():
    result = detect_orphans_diff(
        impl_units=[],
        requirements=[{"id": "REQ-CORE-001"}, {"id": "REQ-CORE-002"}],
        known_ids={"REQ-CORE-001", "REQ-CORE-002"},
        changed_files={"feature_list.json"},
        model_delta_ids={"REQ-CORE-002"},  # only 002 was added
    )
    assert "REQ-CORE-002" in result["backward_orphans"]
    assert "REQ-CORE-001" not in result["backward_orphans"]  # not in delta -> not checked
    assert result["ok"] is False


def test_backward_orphan_never_path_exempt():
    result = detect_orphans_diff(
        impl_units=[],
        requirements=[{"id": "REQ-TOOLS-001"}],
        known_ids={"REQ-TOOLS-001"},
        changed_files={"feature_list.json"},
        model_delta_ids={"REQ-TOOLS-001"},
        allowlist_pattern="tools/.*",  # allowlist affects FORWARD only
    )
    assert "REQ-TOOLS-001" in result["backward_orphans"]
    assert result["ok"] is False


# --- dangling-ref subclass (T1) ----------------------------------------------
def test_dangling_ref_unknown_id():
    result = detect_orphans_diff(
        impl_units=[{"file": "module.py", "text": "# implements REQ-FAKE-999"}],
        requirements=[],
        known_ids={"REQ-REAL-001"},  # non-empty model; REQ-FAKE-999 absent from it
        changed_files={"module.py"},
    )
    assert result.get("dangling_refs", {}).get("REQ-FAKE-999") is not None
    assert result["ok"] is False


def test_wiring_minted_id_not_dangling():
    result = detect_orphans_diff(
        impl_units=[{"file": "impl.py", "text": "# implements REQ-WIRE-001"}],
        requirements=[],
        known_ids={"REQ-REAL-001"},  # REQ-WIRE-001 not yet committed (legit in same PR)
        changed_files={"impl.py"},
    )
    assert result.get("dangling_refs", {}) == {}


# --- merge-base reachability (T4): CI fail-closed / local fallback ------------
def test_ci_fails_closed_on_unreachable_base():
    with patch("tools.orphan_detector._get_merged_base", return_value=None):
        result = detect_orphans_diff(
            impl_units=[], requirements=[], known_ids=set(),
            changed_files=set(), baseline_commit="origin/main",
            fail_closed_on_unreachable=True,  # CI mode
        )
    assert result["ok"] is False
    assert "unreachable" in result.get("error", "").lower()


def test_local_falls_back_to_full_repo():
    result = detect_orphans_diff(
        impl_units=[{"file": "untraceable.py", "text": "# no req"}],
        requirements=[{"id": "REQ-ORPHAN-001"}],
        known_ids={"REQ-ORPHAN-001"},
        changed_files=None,  # None => full-repo fallback
        baseline_commit="origin/main",
        fail_closed_on_unreachable=False,  # local mode
    )
    assert "untraceable.py" in str(result["forward_orphans"])
    assert "REQ-ORPHAN-001" in result["backward_orphans"]
    assert result.get("baseline_fallback_reason") is not None


# --- git helpers (subprocess-mocked) -----------------------------------------
def test_get_merged_base_returns_sha():
    with patch("subprocess.run", return_value=MagicMock(stdout="abc1234\n", returncode=0)):
        assert _get_merged_base("origin/main") == "abc1234"


def test_get_merged_base_none_on_failure():
    with patch("subprocess.run", return_value=MagicMock(stdout="", returncode=128)):
        assert _get_merged_base("origin/main") is None


def test_get_changed_files_splits_lines():
    with patch("subprocess.run", return_value=MagicMock(stdout="a.py\ntools/b.py\n", returncode=0)):
        files = _get_changed_files("origin/main")
    assert files == ["a.py", "tools/b.py"]


def test_load_feature_list_from_commit_parses_json():
    with patch("subprocess.run", return_value=MagicMock(stdout='{"items": [{"id": "REQ-X-001"}]}', returncode=0)):
        content = _load_feature_list_from_commit("HEAD")
    assert content.get("items")[0]["id"] == "REQ-X-001"


def test_load_feature_list_from_commit_missing_returns_empty():
    with patch("subprocess.run", return_value=MagicMock(stdout="", returncode=128)):
        assert _load_feature_list_from_commit("HEAD~1") == {}


def test_filter_keeps_changed_skips_allowlist():
    units = [
        {"file": "tools/helper.py", "text": "x"},
        {"file": "module.py", "text": "y"},
    ]
    filtered = _filter_forward_units_by_changed(
        units, {"tools/helper.py", "module.py"}, allowlist_pattern="tools/.*"
    )
    assert [u["file"] for u in filtered] == ["module.py"]
