import importlib.util, hashlib, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[2]
def _load(rel, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
ART = "art"; HASH = "sha256:" + hashlib.sha256(ART.encode()).hexdigest()
LEDGER = {"sessions": ["i", "v"]}
def _ev(**o):
    r = {"test_file": "t", "test_name": "n", "output_hash": HASH,
         "collected_at": "2026-06-22T00:00:00+00:00",
         "implementer_session_id": "i", "verifier_session_id": "v"}; r.update(o); return r

def test_accept_advances(tmp_path):
    lg = _load("tools/loop_gate.py", "lg")
    rsd = _load("tools/run_state_driver.py", "rsd"); rsd.init(tmp_path, "s")
    r = lg.gated_advance(root=tmp_path, evidence=_ev(), artifact=ART, ledger=LEDGER)
    assert r["action"] == "advance" and r["run_state"]["block_streak"] == 0

def test_reject_self_heals_then_handoffs(tmp_path):
    lg = _load("tools/loop_gate.py", "lg")
    rsd = _load("tools/run_state_driver.py", "rsd"); rsd.init(tmp_path, "s")
    bad = _ev(verifier_session_id="i")   # self-grade
    a = lg.gated_advance(root=tmp_path, evidence=bad, artifact=ART, ledger=LEDGER, max_self_heal=2)
    assert a["action"] == "self_heal" and "verifier" in a["prompt"].lower()
    b = lg.gated_advance(root=tmp_path, evidence=bad, artifact=ART, ledger=LEDGER, max_self_heal=2)
    assert b["action"] == "handoff" and b["code"] == "SAME_SESSION"   # bounded → HANDOFF
