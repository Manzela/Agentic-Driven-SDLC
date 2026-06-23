"""evidence_gate depth checks (Task 4 §4.1-4.2): new CODES/_HEAL + check_slice_semgrep
+ check_slice_orphans. Deterministic — semgrep is subprocess-mocked, orphans use real
temp files (no git). Strong assertions (REQUIRE the reject, not 'if not accepted')."""
import json
import pathlib
import tempfile
from unittest.mock import MagicMock, patch

import tools.evidence_gate as eg


# --- §4.1 new reject codes + heal prompts ------------------------------------
def test_new_codes_present():
    for code in ("SAST_HIGH_CRITICAL", "ORPHAN_DETECTED", "ORPHAN_DANGLING_REF"):
        assert code in eg.CODES


def test_heal_entries_present_and_actionable():
    h = eg._HEAL
    assert "semgrep" in h["SAST_HIGH_CRITICAL"].lower() and "baseline-commit" in h["SAST_HIGH_CRITICAL"].lower()
    assert "existing" in h["ORPHAN_DETECTED"].lower() and "verifier" in h["ORPHAN_DETECTED"].lower()
    assert "id" in h["ORPHAN_DANGLING_REF"].lower() and "seeded" in h["ORPHAN_DANGLING_REF"].lower()
    # self_heal_prompt resolves the new codes
    assert eg.self_heal_prompt({"code": "SAST_HIGH_CRITICAL"}) == h["SAST_HIGH_CRITICAL"]


# --- §4.2 check_slice_semgrep (subprocess-mocked) ----------------------------
def test_semgrep_empty_and_none_skip():
    assert eg.check_slice_semgrep([], "abc")["code"] == "OK"
    assert eg.check_slice_semgrep(None, "abc")["accepted"] is True


def test_semgrep_blocking_finding_rejects():
    # semgrep emits "ERROR" for a blocking finding
    out = json.dumps({"results": [{"extra": {"severity": "ERROR"}}]})
    with patch("subprocess.run", return_value=MagicMock(stdout=out, returncode=1)):
        r = eg.check_slice_semgrep(["m.py"], "base")
    assert r["accepted"] is False and r["code"] == "SAST_HIGH_CRITICAL"


def test_semgrep_clean_returns_ok():
    with patch("subprocess.run", return_value=MagicMock(stdout='{"results": []}', returncode=0)):
        r = eg.check_slice_semgrep(["m.py"], "base")
    assert r["accepted"] is True and r["code"] == "OK"


def test_semgrep_low_severity_not_blocking():
    out = json.dumps({"results": [{"extra": {"severity": "WARNING"}}, {"extra": {"severity": "INFO"}}]})
    with patch("subprocess.run", return_value=MagicMock(stdout=out, returncode=1)):
        r = eg.check_slice_semgrep(["m.py"], "base")
    assert r["accepted"] is True  # only ERROR/HIGH/CRITICAL block


def test_semgrep_missing_binary_fails_open():
    with patch("subprocess.run", side_effect=FileNotFoundError()):
        r = eg.check_slice_semgrep(["m.py"], "base")
    assert r["accepted"] is True and "warn" in r["reason"].lower()


def test_semgrep_malformed_output_fails_open():
    with patch("subprocess.run", return_value=MagicMock(stdout="not json at all", returncode=0)):
        r = eg.check_slice_semgrep(["m.py"], "base")
    assert r["accepted"] is True and r["code"] == "OK"


# --- F1 (red-team): well-formed JSON but wrong shape must FAIL-OPEN, not raise ---
def test_semgrep_null_results_fails_open():
    """{"results": null} is valid JSON but the filter would TypeError on None — must fail-open."""
    with patch("subprocess.run", return_value=MagicMock(stdout='{"results": null}', returncode=1)):
        r = eg.check_slice_semgrep(["m.py"], "base")
    assert r["accepted"] is True and r["code"] == "OK"


def test_semgrep_nonlist_results_fails_open():
    with patch("subprocess.run", return_value=MagicMock(stdout='{"results": {"a": 1}}', returncode=1)):
        r = eg.check_slice_semgrep(["m.py"], "base")
    assert r["accepted"] is True and r["code"] == "OK"


def test_semgrep_nondict_payload_fails_open():
    with patch("subprocess.run", return_value=MagicMock(stdout="[1, 2, 3]", returncode=0)):
        r = eg.check_slice_semgrep(["m.py"], "base")
    assert r["accepted"] is True and r["code"] == "OK"


def test_semgrep_nondict_result_entry_skipped_real_finding_still_blocks():
    """A junk (non-dict) entry inside results is skipped, but a real ERROR still blocks."""
    out = json.dumps({"results": ["junk", {"extra": {"severity": "ERROR"}}]})
    with patch("subprocess.run", return_value=MagicMock(stdout=out, returncode=1)):
        r = eg.check_slice_semgrep(["m.py"], "base")
    assert r["accepted"] is False and r["code"] == "SAST_HIGH_CRITICAL"


def test_semgrep_timeout_is_config_sourced():
    """F6: the subprocess timeout comes from execution_bounds.SEMGREP_TIMEOUT_SECONDS."""
    import tools.execution_bounds as _eb
    captured = {}

    def _fake_run(*a, **k):
        captured["timeout"] = k.get("timeout")
        return MagicMock(stdout='{"results": []}', returncode=0)

    with patch.object(_eb, "SEMGREP_TIMEOUT_SECONDS", 37):
        with patch("subprocess.run", side_effect=_fake_run):
            eg.check_slice_semgrep(["m.py"], "base")
    assert captured["timeout"] == 37


def test_semgrep_baseline_strategy_off_omits_baseline_flag():
    """F6: SEMGREP_BASELINE_STRATEGY='off' must drop --baseline-commit even when given."""
    import tools.execution_bounds as _eb
    captured = {}

    def _fake_run(cmd, *a, **k):
        captured["cmd"] = cmd
        return MagicMock(stdout='{"results": []}', returncode=0)

    with patch.object(_eb, "SEMGREP_BASELINE_STRATEGY", "off"):
        with patch("subprocess.run", side_effect=_fake_run):
            eg.check_slice_semgrep(["m.py"], "base-sha")
    assert "--baseline-commit" not in captured["cmd"]


# --- §4.2 check_slice_orphans (real temp files; delegates to detect_orphans_diff) ---
def _repo(tmp, files: dict, model: dict):
    p = pathlib.Path(tmp)
    (p / "feature_list.json").write_text(json.dumps(model))
    for rel, content in files.items():
        f = p / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(content)
    return str(p / "feature_list.json")


def test_orphans_empty_and_none_skip():
    with tempfile.TemporaryDirectory() as t:
        fl = _repo(t, {}, {"items": []})
        assert eg.check_slice_orphans([], fl, set())["code"] == "OK"
        assert eg.check_slice_orphans(None, fl, set())["accepted"] is True


def test_forward_orphan_rejected():
    with tempfile.TemporaryDirectory() as t:
        fl = _repo(t, {"m.py": "def helper():\n    pass\n"}, {"items": []})
        r = eg.check_slice_orphans(["m.py"], fl, set())
        assert r["accepted"] is False and r["code"] == "ORPHAN_DETECTED"


def test_dangling_ref_rejected():
    with tempfile.TemporaryDirectory() as t:
        # CONSISTENT model (F5): REQ-REAL-001 is a real seeded item; the cited
        # REQ-NONEXIST-999 is absent from it -> dangling. (in_scope:False keeps it out
        # of the backward pass so this isolates the dangling-ref path.)
        fl = _repo(t, {"m.py": "def f():\n    # implements REQ-NONEXIST-999\n    pass\n"},
                   {"items": [{"id": "REQ-REAL-001", "in_scope": False, "status": "unproven"}]})
        r = eg.check_slice_orphans(["m.py"], fl, {"REQ-REAL-001"})
        assert r["accepted"] is False and r["code"] == "ORPHAN_DANGLING_REF"


def test_model_id_not_dangling_even_if_caller_omits_it():
    """F4: caller passes a NON-EMPTY known_ids (cross-check active) but OMITS a real
    seeded id; unioning ids from the loaded model prevents a false dangling flag."""
    with tempfile.TemporaryDirectory() as t:
        fl = _repo(t, {"m.py": "def f():\n    # implements REQ-SEEDED-002\n    pass\n"},
                   {"items": [{"id": "REQ-OTHER-001", "in_scope": False},
                              {"id": "REQ-SEEDED-002", "in_scope": False}]})
        # caller knows REQ-OTHER-001 (activates the cross-check) but NOT REQ-SEEDED-002
        r = eg.check_slice_orphans(["m.py"], fl, {"REQ-OTHER-001"})
        assert r["accepted"] is True and r["code"] == "OK"  # model union saves REQ-SEEDED-002


def test_tools_dir_forward_orphan_exempt():
    with tempfile.TemporaryDirectory() as t:
        fl = _repo(t, {"tools/helper.py": "def internal():\n    pass\n"}, {"items": []})
        r = eg.check_slice_orphans(["tools/helper.py"], fl, set(), allowlist_dirs=("tools/",))
        assert r["accepted"] is True and r["code"] == "OK"


def test_backward_orphan_in_scope_no_artifact_rejected():
    with tempfile.TemporaryDirectory() as t:
        fl = _repo(t, {}, {"items": [{"id": "REQ-TEST-001", "in_scope": True, "status": "unproven"}]})
        r = eg.check_slice_orphans(["feature_list.json"], fl, {"REQ-TEST-001"})
        assert r["accepted"] is False and r["code"] == "ORPHAN_DETECTED"


def test_out_of_scope_backward_not_flagged():
    with tempfile.TemporaryDirectory() as t:
        fl = _repo(t, {}, {"items": [{"id": "REQ-OOS-001", "in_scope": False, "status": "unproven"}]})
        r = eg.check_slice_orphans(["feature_list.json"], fl, {"REQ-OOS-001"})
        assert r["accepted"] is True  # out-of-scope items are not backward orphans


def test_orphans_fail_open_on_internal_error():
    with tempfile.TemporaryDirectory() as t:
        fl = _repo(t, {"m.py": "def f():\n    pass\n"}, {"items": []})
        with patch("tools.orphan_detector.detect_orphans_diff", side_effect=RuntimeError("boom")):
            r = eg.check_slice_orphans(["m.py"], fl, set())
        assert r["accepted"] is True and "fail" in r["reason"].lower()


# --- F2 (red-team): backward pass scoped to model-delta when a baseline is given ---
def test_backward_scoped_to_model_delta_with_baseline():
    """With a baseline_commit, only the PR-introduced (delta) in-scope item is
    backward-checked; a pre-existing in-scope item is NOT flagged (no over-block)."""
    with tempfile.TemporaryDirectory() as t:
        fl = _repo(t, {}, {"items": [
            {"id": "REQ-OLD-001", "in_scope": True, "status": "unproven"},
            {"id": "REQ-NEW-002", "in_scope": True, "status": "unproven"},
        ]})
        baseline = {"items": [{"id": "REQ-OLD-001", "in_scope": True, "status": "unproven"}]}
        with patch("tools.orphan_detector._load_feature_list_from_commit", return_value=baseline):
            r = eg.check_slice_orphans(
                ["feature_list.json"], fl, {"REQ-OLD-001", "REQ-NEW-002"}, baseline_commit="base")
        assert r["accepted"] is False and r["code"] == "ORPHAN_DETECTED"
        assert "REQ-NEW-002" in r["reason"]
        assert "REQ-OLD-001" not in r["reason"]


def test_backward_all_in_scope_without_baseline():
    """Without a baseline_commit, the backward pass conservatively checks ALL in-scope
    items (over-strict, never under) — both pre-existing items flagged."""
    with tempfile.TemporaryDirectory() as t:
        fl = _repo(t, {}, {"items": [
            {"id": "REQ-OLD-001", "in_scope": True, "status": "unproven"},
            {"id": "REQ-NEW-002", "in_scope": True, "status": "unproven"},
        ]})
        r = eg.check_slice_orphans(["feature_list.json"], fl, {"REQ-OLD-001", "REQ-NEW-002"})
        assert r["accepted"] is False and r["code"] == "ORPHAN_DETECTED"
        assert "REQ-OLD-001" in r["reason"]
        assert "REQ-NEW-002" in r["reason"]


def test_unreadable_baseline_falls_back_to_all_in_scope():
    """A baseline commit that yields an empty model ({}) degrades to the conservative
    all-in-scope backward pass rather than scoping to an empty (no-op) delta."""
    with tempfile.TemporaryDirectory() as t:
        fl = _repo(t, {}, {"items": [
            {"id": "REQ-OLD-001", "in_scope": True, "status": "unproven"},
            {"id": "REQ-NEW-002", "in_scope": True, "status": "unproven"},
        ]})
        with patch("tools.orphan_detector._load_feature_list_from_commit", return_value={}):
            r = eg.check_slice_orphans(
                ["feature_list.json"], fl, {"REQ-OLD-001", "REQ-NEW-002"}, baseline_commit="bad")
        assert r["accepted"] is False
        assert "REQ-OLD-001" in r["reason"]
        assert "REQ-NEW-002" in r["reason"]


# --- F3 (red-team): the default allowlist is config-sourced, never hardcoded tools/ ---
def test_allowlist_default_sources_config_not_hardcoded():
    """allowlist_dirs=None honors execution_bounds.ORPHAN_ALLOWLIST_PATTERN (patched to
    src/.*), NOT a hardcoded tools/: src/ becomes exempt and tools/ becomes flagged."""
    with patch("tools.orphan_detector._DEFAULT_ALLOWLIST_PATTERN", "src/.*"):
        with tempfile.TemporaryDirectory() as t:
            fl = _repo(t, {"src/a.py": "def helper():\n    pass\n"}, {"items": []})
            r = eg.check_slice_orphans(["src/a.py"], fl, set())  # default allowlist_dirs=None
            assert r["accepted"] is True
            assert r["code"] == "OK"
        with tempfile.TemporaryDirectory() as t2:
            fl2 = _repo(t2, {"tools/b.py": "def internal():\n    pass\n"}, {"items": []})
            r2 = eg.check_slice_orphans(["tools/b.py"], fl2, set())
            assert r2["accepted"] is False
            assert r2["code"] == "ORPHAN_DETECTED"
