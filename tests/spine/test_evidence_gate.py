# tests/spine/test_evidence_gate.py
import importlib.util, hashlib, pathlib, pytest
ROOT = pathlib.Path(__file__).resolve().parents[2]
def _load():
    spec = importlib.util.spec_from_file_location("eg", ROOT / "tools/evidence_gate.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

ART = "the-real-artifact-bytes"
HASH = "sha256:" + hashlib.sha256(ART.encode()).hexdigest()
LEDGER = {"sessions": ["sess-impl", "sess-veri"]}
def _ev(**over):
    rec = {"test_file": "t.py", "test_name": "t::case", "output_hash": HASH,
           "collected_at": "2026-06-22T00:00:00+00:00",
           "implementer_session_id": "sess-impl", "verifier_session_id": "sess-veri"}
    rec.update(over); return rec

def test_valid_slice_accepted():
    eg = _load()
    r = eg.check_slice(evidence=_ev(), artifact=ART, ledger=LEDGER)
    assert r["accepted"] is True and r["code"] == "OK"

def test_missing_evidence_rejected():
    eg = _load()
    r = eg.check_slice(evidence=None, artifact=ART, ledger=LEDGER)
    assert r["accepted"] is False and r["code"] == "EVIDENCE_MISSING"

def test_malformed_four_field_rejected():
    eg = _load()
    r = eg.check_slice(evidence=_ev(output_hash="sha256:NOThex"), artifact=ART, ledger=LEDGER)
    assert r["accepted"] is False and r["code"] == "EVIDENCE_MALFORMED"

def test_hash_mismatch_rejected():           # RED-TEAM: forged hash of a different artifact
    eg = _load()
    r = eg.check_slice(evidence=_ev(), artifact="a-DIFFERENT-artifact", ledger=LEDGER)
    assert r["accepted"] is False and r["code"] == "HASH_MISMATCH"

def test_same_session_self_grade_rejected():  # RED-TEAM: implementer self-verifies
    eg = _load()
    r = eg.check_slice(evidence=_ev(verifier_session_id="sess-impl"), artifact=ART, ledger=LEDGER)
    assert r["accepted"] is False and r["code"] == "SAME_SESSION"

def test_session_not_in_ledger_rejected():    # RED-TEAM: spoofed session id
    eg = _load()
    r = eg.check_slice(evidence=_ev(verifier_session_id="sess-GHOST"), artifact=ART, ledger=LEDGER)
    assert r["accepted"] is False and r["code"] == "SESSION_NOT_IN_LEDGER"

def test_missing_session_ids_rejected():
    eg = _load()
    ev = _ev(); del ev["verifier_session_id"]
    r = eg.check_slice(evidence=ev, artifact=ART, ledger=LEDGER)
    assert r["accepted"] is False and r["code"] == "SESSION_MISSING"

def test_no_artifact_fails_closed():
    eg = _load()
    r = eg.check_slice(evidence=_ev(), artifact=None, ledger=LEDGER)
    assert r["accepted"] is False and r["code"] == "HASH_MISMATCH"

def test_self_heal_prompt_is_action_directive():
    eg = _load()
    p = eg.self_heal_prompt(eg.check_slice(evidence=_ev(verifier_session_id="sess-impl"),
                                           artifact=ART, ledger=LEDGER))
    assert "verifier" in p.lower() and "session" in p.lower()  # names the corrective action

def test_check_model_collects_rejections():
    eg = _load()
    model = {"items": [
        {"id": "A", "in_scope": True, "status": "proven", "evidence": _ev()},
        {"id": "B", "in_scope": True, "status": "proven", "evidence": _ev(verifier_session_id="sess-impl")},
        {"id": "C", "in_scope": False, "status": "unproven"}]}
    r = eg.check_model(model=model, ledger=LEDGER, artifacts={"A": ART, "B": ART})
    assert r["accepted"] is False
    assert [x["id"] for x in r["rejections"]] == ["B"]   # only the self-grade; C is out-of-scope

# ---- check_model fail-closed red team (a malformed model must NEVER vacuously accept) ----

def test_check_model_none_fails_closed():     # RED-TEAM: model is None (was uncaught AttributeError)
    eg = _load()
    r = eg.check_model(model=None, ledger=LEDGER, artifacts={})
    assert r["accepted"] is False and r["rejections"][0]["code"] == "MODEL_MALFORMED"

def test_check_model_items_non_int_fails_closed():  # RED-TEAM: items is an int (was uncaught TypeError)
    eg = _load()
    r = eg.check_model(model={"items": 5}, ledger=LEDGER, artifacts={})
    assert r["accepted"] is False and r["rejections"][0]["code"] == "MODEL_MALFORMED"

def test_check_model_items_string_not_vacuous_accept():  # RED-TEAM: the dangerous silent-pass case
    eg = _load()
    r = eg.check_model(model={"items": "x"}, ledger=LEDGER, artifacts={})
    assert r["accepted"] is False and r["rejections"][0]["code"] == "MODEL_MALFORMED"

def test_check_model_non_dict_item_fails_closed():  # RED-TEAM: list with a non-dict element
    eg = _load()
    r = eg.check_model(model={"items": [{"id": "A", "in_scope": True, "status": "proven",
                                        "evidence": _ev()}, "junk"]},
                       ledger=LEDGER, artifacts={"A": ART})
    assert r["accepted"] is False and r["rejections"][0]["code"] == "MODEL_MALFORMED"

def test_check_model_empty_items_accepts():   # nothing in scope is a legitimate accept (not vacuous-malformed)
    eg = _load()
    r = eg.check_model(model={"items": []}, ledger=LEDGER, artifacts={})
    assert r["accepted"] is True and r["rejections"] == []
