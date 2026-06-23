"""Actor-independence fix #5: Z3 proves a proven item implies distinct actors,
and the runtime gate refuses any same-session evidence."""
import hashlib
import importlib.util
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]


def test_z3_proves_separation():
    z3 = pytest.importorskip("z3")  # skip cleanly if the solver is unavailable
    from verification.actor_separation import prove
    assert prove() == "UNSAT-to-violate"


def test_runtime_gate_refuses_same_session():
    p = ROOT / ".claude/hooks/subagent_stop_hook.py"
    spec = importlib.util.spec_from_file_location("subagent_stop_hook", p)
    hook = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(hook)
    output = "x"
    rec = {
        "test_file": "t", "test_name": "n",
        "output_hash": "sha256:" + hashlib.sha256(output.encode()).hexdigest(),
        "collected_at": "2026-06-15T00:00:00+00:00", "actor_agent": "verifier",
        "verifier_session_id": "s", "implementer_session_id": "s",
    }
    assert hook.evaluate(rec, output, "verifier", "[Gap] none")["decision"] == "block"
