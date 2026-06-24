"""Phase-1 verification-depth integration suite — the T1–T12 red-team evasion oracle.

Each test mounts a real evasion attempt against the live component and asserts the gate
rejects it (or routes the fix to the verifier). This is the consolidated adversarial
proof that the Phase-1 threat model holds end-to-end; the per-component suites prove the
mechanisms, this proves the THREATS are defended.

Threat map (spec §8):
  T1  fabricated req-id -> dangling-ref forward orphan
  T2  bare/outside-tools exempt markers are NOT self-exemptions
  T3  backward orphan scoped to the model-delta
  T4  CI merge-base unreachable -> fail-CLOSED
  T8  proven WIRING needs integration evidence (unit-evidence denied)
  T9  born-proven insertion denied (only the verifier proves)
  T10 non-verifier deletion of an in-scope/unproven item denied (append-only)
  T11 born-in_scope:false insertion denied (human-owned scope)
  T12 MultiEdit status/in_scope flip is parsed and denied
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import coverage_gate  # noqa: E402
from tools.orphan_detector import detect_orphans, detect_orphans_diff  # noqa: E402


def _hook():
    spec = importlib.util.spec_from_file_location(
        "pre_tool_use_hook", ROOT / ".claude/hooks/pre_tool_use_hook.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


HOOK = _hook()


def _doc(id_, status="unproven", in_scope=True):
    sc = "true" if in_scope else "false"
    return f'{{"items":[{{"id":"{id_}","status":"{status}","in_scope":{sc}}}]}}'


def _evidence(kind="integration", **over):
    ev = {"test_file": "t", "test_name": "n", "output_hash": "sha256:" + "a" * 64,
          "collected_at": "2026-06-16T00:00:00+00:00",
          "implementer_session_id": "i", "verifier_session_id": "v", "evidence_kind": kind}
    ev.update(over)
    return ev


# ── T1: fabricated requirement id is a dangling-ref forward orphan ────────────
def test_t1_fabricated_req_id_dangling_ref():
    known_ids = {"REQ-REAL-001"}
    impl_units = [{"file": "mod.py", "text": "def f():\n    # implements REQ-NONEXIST-999\n    pass\n"}]
    report = detect_orphans(impl_units, [{"id": "REQ-REAL-001"}], known_ids=known_ids)
    assert not report["ok"]
    assert "REQ-NONEXIST-999" in json.dumps(report)


def test_t1_real_wiring_id_not_dangling():
    """A REQ-WIRE-* reference (minted in-PR, not yet committed) is exempt — not dangling."""
    impl_units = [{"file": "m.py", "text": "# implements REQ-WIRE-001\n"}]
    report = detect_orphans(impl_units, [{"id": "REQ-REAL-001"}], known_ids={"REQ-REAL-001"})
    assert "REQ-WIRE-001" not in json.dumps(report.get("dangling_refs", {}))


# ── T2: exempt markers cannot be self-granted ────────────────────────────────
def test_t2_bare_orphan_exempt_not_honored():
    """A bare `# orphan-exempt` (no reason) is NOT an exemption — still an orphan."""
    impl_units = [{"file": "m.py", "text": "def helper():  # orphan-exempt\n    pass\n"}]
    report = detect_orphans(impl_units, [], known_ids=set())
    assert not report["ok"], "a reasonless orphan-exempt must not self-exempt"


def test_t2_reasoned_exempt_is_honored():
    impl_units = [{"file": "m.py", "text": "def helper():  # orphan-exempt: shared util, no req\n    pass\n"}]
    report = detect_orphans(impl_units, [], known_ids=set())
    assert report["ok"], "a reasoned orphan-exempt IS honored"


# ── T3: backward orphan is scoped to the model-delta ─────────────────────────
def test_t3_backward_orphan_model_delta_blocks():
    report = detect_orphans_diff(
        impl_units=[], requirements=[{"id": "REQ-NEW-002"}], known_ids={"REQ-NEW-002"},
        changed_files={"feature_list.json"}, model_delta_ids={"REQ-NEW-002"})
    assert "REQ-NEW-002" in report["backward_orphans"]
    assert report["ok"] is False


def test_t3_pre_existing_item_not_in_delta_not_blocked():
    report = detect_orphans_diff(
        impl_units=[], requirements=[{"id": "REQ-OLD-001"}, {"id": "REQ-NEW-002"}],
        known_ids={"REQ-OLD-001", "REQ-NEW-002"}, changed_files={"feature_list.json"},
        model_delta_ids={"REQ-NEW-002"})
    assert "REQ-OLD-001" not in report["backward_orphans"]  # not in delta -> not checked


# ── T4: CI merge-base unreachable -> fail-CLOSED ─────────────────────────────
def test_t4_merge_base_unreachable_fails_closed():
    with patch("tools.orphan_detector._get_merged_base", return_value=None):
        report = detect_orphans_diff(
            impl_units=[], requirements=[], known_ids=set(), changed_files=set(),
            baseline_commit="origin/main", fail_closed_on_unreachable=True)
    assert report["ok"] is False
    assert "unreachable" in report.get("error", "").lower()


# ── T8: proven WIRING must carry integration evidence ────────────────────────
def test_t8_proven_wiring_with_unit_evidence_denied():
    model = {"items": [{"id": "REQ-WIRE-001", "type": "WIRING", "in_scope": True,
                        "status": "proven", "evidence": _evidence(kind="unit")}]}
    assert coverage_gate.deny_merge(model)["deny"] is True


def test_t8_proven_wiring_with_integration_evidence_allowed():
    model = {"items": [{"id": "REQ-WIRE-001", "type": "WIRING", "in_scope": True,
                        "status": "proven", "evidence": _evidence(kind="integration")}]}
    assert coverage_gate.deny_merge(model)["deny"] is False


# ── T9: born-proven insertion denied ─────────────────────────────────────────
def test_t9_new_item_born_proven_blocked():
    out = HOOK.evaluate(tool_name="Edit", resolved_actor="implementer", human_signed=False,
                        tool_input={"file_path": "feature_list.json",
                                    "old_string": '{"items":[]}',
                                    "new_string": _doc("F-9", status="proven")})
    assert out["decision"] == "block"


def test_t9_verifier_may_birth_proven():
    out = HOOK.evaluate(tool_name="Edit", resolved_actor="verifier", human_signed=False,
                        tool_input={"file_path": "feature_list.json",
                                    "old_string": '{"items":[]}',
                                    "new_string": _doc("F-9", status="proven")})
    assert out["decision"] == "allow"


# ── T10: non-verifier deletion of an in-scope/unproven item denied ───────────
def test_t10_deletion_of_unproven_item_blocked():
    out = HOOK.evaluate(tool_name="Edit", resolved_actor="implementer", human_signed=False,
                        tool_input={"file_path": "feature_list.json",
                                    "old_string": _doc("F-1"), "new_string": '{"items":[]}'})
    assert out["decision"] == "block"
    assert "delet" in out["reason"].lower() or "append" in out["reason"].lower()


# ── T11: born out-of-scope insertion denied ──────────────────────────────────
def test_t11_born_out_of_scope_insertion_blocked():
    out = HOOK.evaluate(tool_name="Edit", resolved_actor="initializer", human_signed=False,
                        tool_input={"file_path": "feature_list.json",
                                    "old_string": '{"items":[]}',
                                    "new_string": _doc("F-9", in_scope=False)})
    assert out["decision"] == "block"
    assert "in_scope" in out["reason"].lower()


def test_t11_human_signed_may_birth_out_of_scope():
    out = HOOK.evaluate(tool_name="Edit", resolved_actor="initializer", human_signed=True,
                        tool_input={"file_path": "feature_list.json",
                                    "old_string": '{"items":[]}',
                                    "new_string": _doc("F-9", in_scope=False)})
    assert out["decision"] == "allow"


# ── T12: MultiEdit status/in_scope flip parsed and denied ────────────────────
def test_t12_multiedit_status_flip_detected():
    out = HOOK.evaluate(tool_name="MultiEdit", resolved_actor="implementer", human_signed=False,
                        tool_input={"file_path": "feature_list.json",
                                    "edits": [{"old_string": '"status":"unproven"',
                                               "new_string": '"status":"proven"'}]})
    assert out["decision"] == "block"


# ── granularity: tools/ forward-exempt; function-level units ─────────────────
def test_granularity_tools_forward_exempt():
    report = detect_orphans_diff(
        impl_units=[{"file": "tools/helper.py", "text": "# no req"}], requirements=[],
        known_ids={"REQ-X-001"}, changed_files={"tools/helper.py"}, allowlist_pattern="tools/.*")
    assert report["ok"] is True


def test_granularity_changed_file_orphan_flagged():
    report = detect_orphans_diff(
        impl_units=[{"file": "new_module.py", "text": "def foo(): pass"}], requirements=[],
        known_ids={"REQ-X-001"}, changed_files={"new_module.py"})
    assert "new_module.py" in str(report["forward_orphans"])
    assert report["ok"] is False
