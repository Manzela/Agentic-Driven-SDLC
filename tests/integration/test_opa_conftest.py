"""Conftest/OPA integration test: the rego merge policy is the faithful twin of the
Python gate coverage_gate.deny_merge (Task 9 / tasks 21.3 / 26.1).

Runs the REAL `conftest test <model> --policy .github/policies/` and asserts the rego
deny set agrees with coverage_gate.deny_merge on the same input — in particular the new
WIRING integration-evidence rule (Rule 5 / Rule 4). Skipped when conftest is not
installed; CI installs it so the twin is gated there.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
POLICY_DIR = ROOT / ".github" / "policies"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import coverage_gate  # noqa: E402

pytestmark = pytest.mark.skipif(
    shutil.which("conftest") is None,
    reason="conftest not installed; the rego twin is gated in CI (Task 15)",
)


def _conftest_denies(model: dict, tmp_path: Path) -> bool:
    """True iff conftest produced at least one deny over `model`. conftest exits
    non-zero when any deny rule fires, 0 when the policy is fully satisfied."""
    f = tmp_path / "feature_list.json"
    f.write_text(json.dumps(model))
    proc = subprocess.run(
        ["conftest", "test", str(f), "--policy", str(POLICY_DIR), "--no-color"],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    return proc.returncode != 0


def _ev(kind=None, **over):
    ev = {"test_file": "t", "test_name": "n", "output_hash": "sha256:" + "a" * 64,
          "collected_at": "2026-06-16T00:00:00+00:00",
          "implementer_session_id": "sess-i", "verifier_session_id": "sess-v"}
    if kind is not None:
        ev["evidence_kind"] = kind
    ev.update(over)
    return ev


def _wiring(kind, **over):
    item = {"id": "REQ-WIRE-001", "type": "WIRING", "in_scope": True,
            "status": "proven", "evidence": _ev(kind)}
    item.update(over)
    return {"items": [item]}


def test_wiring_unit_evidence_denied_by_rego(tmp_path: Path) -> None:
    """Rule 5: a proven WIRING item with evidence_kind='unit' is denied."""
    assert _conftest_denies(_wiring("unit"), tmp_path) is True


def test_wiring_integration_evidence_allowed_by_rego(tmp_path: Path) -> None:
    """Rule 5: a proven WIRING item with evidence_kind='integration' (otherwise
    complete + distinct sessions) is NOT denied."""
    assert _conftest_denies(_wiring("integration"), tmp_path) is False


# Fixtures spanning the deny rules — rego and the Python twin must AGREE on each.
_PARITY_MODELS = {
    "wiring_unit": lambda: _wiring("unit"),                       # Rule 5 deny
    "wiring_behavioral": lambda: _wiring("behavioral"),           # Rule 5 deny
    "wiring_missing_kind": lambda: _wiring(None),                 # Rule 5 deny (absent)
    "wiring_integration_ok": lambda: _wiring("integration"),      # allow
    "functional_proven_ok": lambda: {"items": [
        {"id": "REQ-FUNC-001", "type": "functional", "in_scope": True,
         "status": "proven", "evidence": _ev()}]},                # allow (kind irrelevant)
    "inscope_unproven": lambda: {"items": [
        {"id": "REQ-A-001", "type": "functional", "in_scope": True, "status": "unproven"}]},
    "empty_model": lambda: {"items": []},                         # Rule 3 deny
    "self_graded_wiring": lambda: _wiring(
        "integration", evidence=_ev("integration", implementer_session_id="x",
                                    verifier_session_id="x")),    # Rule 4 (actor) deny
    # Non-string four-field values: schema is type:string, so each is invalid evidence
    # and BOTH twins must deny (red-team: rego missed null/[]/number, python missed
    # false — a twin split this fixture set now gates).
    "field_false": lambda: {"items": [{"id": "REQ-F-001", "type": "functional",
        "in_scope": True, "status": "proven", "evidence": _ev(test_file=False)}]},
    "field_null": lambda: {"items": [{"id": "REQ-F-001", "type": "functional",
        "in_scope": True, "status": "proven", "evidence": _ev(output_hash=None)}]},
    "field_empty_list": lambda: {"items": [{"id": "REQ-F-001", "type": "functional",
        "in_scope": True, "status": "proven", "evidence": _ev(test_name=[])}]},
    "field_number": lambda: {"items": [{"id": "REQ-F-001", "type": "functional",
        "in_scope": True, "status": "proven", "evidence": _ev(collected_at=42)}]},
}


@pytest.mark.parametrize("name", sorted(_PARITY_MODELS))
def test_rego_twin_parity_with_python_gate(name, tmp_path: Path) -> None:
    """The rego deny set agrees with coverage_gate.deny_merge for every fixture —
    the OPA twin and the Python gate are kept logically identical."""
    model = _PARITY_MODELS[name]()
    rego_denies = _conftest_denies(model, tmp_path)
    python_denies = coverage_gate.deny_merge(model)["deny"]
    assert rego_denies == python_denies, (
        f"{name}: rego_denies={rego_denies} != python_denies={python_denies}")
