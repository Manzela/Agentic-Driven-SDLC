"""Unit tests for the plane_client completion-gate logic (pure, no network).

Covers the audit's P0 gate fixes: gate-ORDER enforcement (REL-02) and
credential-gated actor independence (SEC-03).
"""
import os
import sys
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "plane-integration"))

# plane_client resolves board config at import; give it dummy env so import never
# touches credentials.env or the network.
os.environ.setdefault("PLANE_API_BASE", "http://test.invalid/api/v1")
os.environ.setdefault("PLANE_WS", "t")
os.environ.setdefault("PLANE_PROJ", "p")
os.environ.setdefault("PLANE_API_KEY", "k")

import plane_client as pc  # noqa: E402


# ── gate ORDER (REL-02) ───────────────────────────────────────────────────────
@pytest.mark.parametrize("cur,to", [
    ("Backlog", "Agent-Triaged"),
    ("Plan-Approved", "Agent-Executing"),
    ("Agent-Executing", "In-Verification"),
    ("In-Verification", "Human-Review"),
    ("Human-Review", "Done"),
    ("In-Verification", "Done"),        # EXTRA_EDGES: verifier shortcut
    ("Agent-Executing", "Blocked"),     # universal escape
    ("Spec-Compiling", "HANDOFF"),      # universal escape
    ("Blocked", "Agent-Executing"),     # recovery
])
def test_legal_edges(cur, to):
    assert pc.legal_edge(cur, to) is True


@pytest.mark.parametrize("cur,to", [
    ("Backlog", "Done"),                # the headline bug: can't jump to Done
    ("Spec-Verified", "Done"),
    ("Agent-Triaged", "Agent-Executing"),  # skipping states
    ("Done", "Agent-Executing"),        # terminal has no outbound
    ("HANDOFF", "Agent-Executing"),
    ("Failed", "Done"),
    ("Agent-Executing", "Agent-Executing"),  # self-edge
])
def test_illegal_edges(cur, to):
    assert pc.legal_edge(cur, to) is False


# ── actor independence (SEC-03) ───────────────────────────────────────────────
def test_wrong_role_rejected():
    with pytest.raises(PermissionError):
        pc.check_actor("implementer", "Done", env={})


def test_privileged_role_requires_secret():
    # verifier is authorized for Done, but without the secret it must be rejected
    with pytest.raises(PermissionError):
        pc.check_actor("verifier", "Done", env={})


def test_privileged_role_with_secret_ok():
    pc.check_actor("verifier", "Done", env={"ASCP_VERIFIER_SECRET": "s"})  # no raise


def test_human_gate_requires_human_secret():
    with pytest.raises(PermissionError):
        pc.check_actor("human", "Plan-Approved", env={})
    pc.check_actor("human", "Plan-Approved", env={"ASCP_HUMAN_SECRET": "s"})


def test_nonprivileged_role_no_secret_needed():
    pc.check_actor("implementer", "Agent-Executing", env={})  # no raise
    pc.check_actor("initializer", "Spec-Compiling", env={})


# ── evidence validation (REL-03) shares the collector contract ────────────────
def test_evidence_validation_contract():
    from tools.evidence_collector import validate_evidence_record
    good = {"test_file": "t.py", "test_name": "x", "collected_at": "2026-06-18T00:00:00+00:00",
            "output_hash": "sha256:" + "a" * 64}
    assert validate_evidence_record(good) is True
    assert validate_evidence_record({**good, "output_hash": "deadbeef"}) is False   # bad format
    assert validate_evidence_record({**good, "test_name": ""}) is False             # empty field
