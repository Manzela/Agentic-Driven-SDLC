# tests/plane/test_the_loop_gated_prove.py
import importlib.util, hashlib, pathlib, sys, types
ROOT = pathlib.Path(__file__).resolve().parents[2]
def test_prove_blocks_self_grade(monkeypatch, tmp_path):
    # stub plane_client so the_loop imports without a live board
    pc = types.ModuleType("plane_client"); pc.PBASE = ""; pc.STATES = {}
    pc.transition = lambda *a, **k: (_ for _ in ()).throw(AssertionError("must NOT transition on reject"))
    pc.post_evidence = lambda *a, **k: None
    sys.modules["plane_client"] = pc
    spec = importlib.util.spec_from_file_location("the_loop", ROOT / "plane-integration/the_loop.py")
    tl = importlib.util.module_from_spec(spec); spec.loader.exec_module(tl)
    # a self-grade slice (verifier==implementer) must be refused, not set Done
    out = tl.gated_prove(issue_id="X", evidence={
        "test_file":"t","test_name":"n",
        "output_hash":"sha256:"+hashlib.sha256(b"a").hexdigest(),
        "collected_at":"2026-06-22T00:00:00+00:00",
        "implementer_session_id":"i","verifier_session_id":"i"},
        artifact="a", ledger={"sessions":["i"]}, root=tmp_path)
    assert out["action"] in ("self_heal", "handoff")  # never advance/Done
