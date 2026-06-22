import importlib.util, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[2]
def _cg():
    spec = importlib.util.spec_from_file_location("cg", ROOT / "tools/coverage_gate.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
def _ev(**o):
    r = {"test_file":"t","test_name":"n","output_hash":"sha256:"+"a"*64,
         "collected_at":"2026-06-22T00:00:00+00:00",
         "implementer_session_id":"i","verifier_session_id":"v"}; r.update(o); return r
def _item(ev):
    return {"items":[{"id":"A","in_scope":True,"status":"proven","evidence":ev}]}
def test_same_session_denies_merge():
    cg = _cg()
    m = _item(_ev(verifier_session_id="i"))
    res = cg.deny_merge(m)
    assert res["deny"] is True and any("session" in r.lower() for r in res["reasons"])
def test_missing_session_denies_merge():
    cg = _cg(); ev = _ev(); del ev["verifier_session_id"]
    res = cg.deny_merge(_item(ev))
    assert res["deny"] is True
def test_distinct_sessions_pass_actor_sep():
    cg = _cg()
    res = cg.deny_merge(_item(_ev()))
    assert res["deny"] is False

# ── Red-team: near-duplicate session ids the gate MUST reject ─────────────────
# These are forgeries the un-normalized gate WRONGLY accepted as 'distinct':
# an implementer that implemented as 'i' submitting a whitespace-padded or
# case-variant verifier id to dodge the self-grading check. The normalized gate
# must collapse them to the same actor and deny.
def test_whitespace_padded_session_is_self_grading():
    cg = _cg()
    # implementer='i', verifier=' i ' — same actor after strip.
    res = cg.deny_merge(_item(_ev(implementer_session_id="i", verifier_session_id=" i ")))
    assert res["deny"] is True
    assert any("session" in r.lower() for r in res["reasons"])
def test_case_variant_session_is_self_grading():
    cg = _cg()
    # implementer='i', verifier='I' — same actor after case-fold.
    res = cg.deny_merge(_item(_ev(implementer_session_id="i", verifier_session_id="I")))
    assert res["deny"] is True
    assert any("session" in r.lower() for r in res["reasons"])
def test_mixed_whitespace_and_case_is_self_grading():
    cg = _cg()
    # implementer=' Impl-1 ', verifier='impl-1' — same after strip+case-fold.
    res = cg.deny_merge(_item(_ev(implementer_session_id=" Impl-1 ", verifier_session_id="impl-1")))
    assert res["deny"] is True
    assert any("session" in r.lower() for r in res["reasons"])
def test_whitespace_only_session_treated_as_absent():
    cg = _cg()
    # A whitespace-only verifier id normalizes to "" -> treated as absent -> deny.
    res = cg.deny_merge(_item(_ev(verifier_session_id="   ")))
    assert res["deny"] is True
def test_non_string_session_treated_as_absent():
    cg = _cg()
    # A non-string verifier id normalizes to "" -> treated as absent -> deny.
    res = cg.deny_merge(_item(_ev(verifier_session_id=12345)))
    assert res["deny"] is True
def test_distinct_after_normalization_still_passes():
    cg = _cg()
    # ' Impl ' vs ' Verify ' are genuinely distinct after normalization.
    res = cg.deny_merge(_item(_ev(implementer_session_id=" Impl ", verifier_session_id=" Verify ")))
    assert res["deny"] is False

# ── Direct unit coverage of the normalization helper ─────────────────────────
def test_norm_session_helper():
    cg = _cg()
    assert cg._norm_session(" i ") == "i"
    assert cg._norm_session("I") == "i"
    assert cg._norm_session("  Impl-1  ") == "impl-1"
    assert cg._norm_session("   ") == ""
    assert cg._norm_session(None) == ""
    assert cg._norm_session(12345) == ""
