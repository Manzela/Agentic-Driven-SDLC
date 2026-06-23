"""Independent verifier tests for tools/coverage_gate.py + the OPA twin
.github/policies/coverage_query.rego (S-coverage_gate).

REQ-GATE-002 / Property 22 / task 21 — the zero-evidence merge gate.

Written independently of the implementer. The contract under test:

  * an in-scope UNPROVEN item            -> deny True, with a reason
  * an in-scope PROVEN item missing
    output_hash (partial Evidence_Record) -> deny True
  * a FAILED in-scope item (status != "proven") -> deny True
  * ALL in-scope items proven + complete  -> deny False
  * OUT-OF-SCOPE unproven items are ignored (never deny)

Also asserts the .rego twin exists and references both "deny" and
"in_scope" so the OPA form cannot silently drift to an empty policy.
"""
from pathlib import Path

from tools.coverage_gate import deny_merge

REPO_ROOT = Path(__file__).resolve().parents[2]
REGO_PATH = REPO_ROOT / ".github" / "policies" / "coverage_query.rego"


def _complete_evidence(tag: str = "x") -> dict:
    """A complete four-field Evidence_Record.

    Carries DISTINCT implementer/verifier session ids as provenance alongside the
    four-field record so it satisfies the actor-separation gate (Rule 3). The
    session ids are NOT part of the four-field validator; they are provenance.
    """
    return {
        "test_file": f"tests/spine/test_{tag}.py",
        "test_name": f"test_{tag}",
        "output_hash": f"sha256:{tag * 8}",
        "collected_at": "2026-06-16T00:00:00Z",
        "implementer_session_id": f"impl-{tag}",
        "verifier_session_id": f"veri-{tag}",
    }


def _proven(item_id: str) -> dict:
    return {
        "id": item_id,
        "in_scope": True,
        "status": "proven",
        "evidence": _complete_evidence(item_id),
    }


# --------------------------------------------------------------------------- #
# in-scope UNPROVEN item -> deny True with a reason
# --------------------------------------------------------------------------- #
def test_in_scope_unproven_item_denies_with_reason():
    fl = {
        "items": [
            {"id": "A", "in_scope": True, "status": "unproven"},
        ]
    }
    result = deny_merge(fl)

    assert result["deny"] is True
    assert isinstance(result["reasons"], list)
    assert result["reasons"], "expected at least one deny reason"
    # the reason must actually name the offending item
    assert any("A" in r for r in result["reasons"])


# --------------------------------------------------------------------------- #
# in-scope PROVEN item missing output_hash -> deny True
# --------------------------------------------------------------------------- #
def test_in_scope_proven_missing_output_hash_denies():
    ev = _complete_evidence("B")
    ev.pop("output_hash")  # proven but Evidence_Record is incomplete
    fl = {
        "items": [
            {"id": "B", "in_scope": True, "status": "proven", "evidence": ev},
        ]
    }
    result = deny_merge(fl)

    assert result["deny"] is True
    assert any("output_hash" in r for r in result["reasons"]), result["reasons"]


# --------------------------------------------------------------------------- #
# FAILED in-scope item (status != "proven") -> deny True
# --------------------------------------------------------------------------- #
def test_in_scope_failed_item_denies():
    fl = {
        "items": [
            {
                "id": "C",
                "in_scope": True,
                "status": "failed",
                "evidence": _complete_evidence("C"),  # even with full evidence
            },
        ]
    }
    result = deny_merge(fl)

    assert result["deny"] is True
    assert any("C" in r for r in result["reasons"])


# --------------------------------------------------------------------------- #
# all in-scope proven + complete -> deny False
# --------------------------------------------------------------------------- #
def test_all_in_scope_proven_complete_allows():
    fl = {
        "items": [
            _proven("D"),
            _proven("E"),
        ]
    }
    result = deny_merge(fl)

    assert result["deny"] is False, result["reasons"]
    assert result["reasons"] == []


# --------------------------------------------------------------------------- #
# out-of-scope unproven items are ignored
# --------------------------------------------------------------------------- #
def test_out_of_scope_unproven_items_are_ignored():
    fl = {
        "items": [
            _proven("F"),  # the only in-scope item, fully proven
            {"id": "G", "in_scope": False, "status": "unproven"},
            {"id": "H", "in_scope": False, "status": "failed"},
        ]
    }
    result = deny_merge(fl)

    assert result["deny"] is False, result["reasons"]
    assert result["reasons"] == []


# --------------------------------------------------------------------------- #
# the .rego twin exists and is a real policy (not an empty stub)
# --------------------------------------------------------------------------- #
def test_rego_policy_exists_and_references_deny_and_in_scope():
    assert REGO_PATH.exists(), f"missing OPA policy at {REGO_PATH}"
    text = REGO_PATH.read_text(encoding="utf-8")
    assert "deny" in text, "rego policy has no 'deny' rule"
    assert "in_scope" in text, "rego policy does not filter on 'in_scope'"
