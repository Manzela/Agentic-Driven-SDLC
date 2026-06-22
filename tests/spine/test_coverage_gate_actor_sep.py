import importlib.util, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[2]
def _cg():
    spec = importlib.util.spec_from_file_location("cg", ROOT / "tools/coverage_gate.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
def _ev(**o):
    r = {"test_file":"t","test_name":"n","output_hash":"sha256:"+"a"*64,
         "collected_at":"2026-06-22T00:00:00+00:00",
         "implementer_session_id":"i","verifier_session_id":"v"}; r.update(o); return r
def test_same_session_denies_merge():
    cg = _cg()
    m = {"items":[{"id":"A","in_scope":True,"status":"proven","evidence":_ev(verifier_session_id="i")}]}
    res = cg.deny_merge(m)
    assert res["deny"] is True and any("session" in r.lower() for r in res["reasons"])
def test_missing_session_denies_merge():
    cg = _cg(); ev = _ev(); del ev["verifier_session_id"]
    res = cg.deny_merge({"items":[{"id":"A","in_scope":True,"status":"proven","evidence":ev}]})
    assert res["deny"] is True
def test_distinct_sessions_pass_actor_sep():
    cg = _cg()
    res = cg.deny_merge({"items":[{"id":"A","in_scope":True,"status":"proven","evidence":_ev()}]})
    assert res["deny"] is False
