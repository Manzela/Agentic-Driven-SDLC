# tests/spine/test_baseline_gate.py
import importlib.util, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[2]
def _load():
    s = importlib.util.spec_from_file_location("bg", ROOT / "tools/baseline_gate.py")
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
def _fl(*ids_in_scope, extra=()):
    items = [{"id": i, "in_scope": True, "status": "proven"} for i in ids_in_scope]
    items += [{"id": i, "in_scope": False} for i in extra]
    return {"items": items}

def test_no_baseline_is_pre_delivery_allow():
    bg = _load()
    assert bg.baseline_gate(baseline=None, feature_list=None)["deny"] is False
    assert bg.baseline_gate(baseline={"required_in_scope": []}, feature_list=None)["deny"] is False

def test_RT01_absent_model_when_delivery_expected_denies():
    bg = _load()
    r = bg.baseline_gate(baseline={"required_in_scope": ["A", "B"]}, feature_list=None)
    assert r["deny"] is True and any("absent" in x.lower() or "missing" in x.lower() for x in r["reasons"])

def test_RT02_item_flipped_out_of_scope_denies():
    bg = _load()
    # baseline requires A,B in scope; payload keeps A in scope but drops B to out-of-scope
    r = bg.baseline_gate(baseline={"required_in_scope": ["A", "B"]},
                         feature_list=_fl("A", extra=("B",)))
    assert r["deny"] is True and any("B" in x for x in r["reasons"])

def test_RT02_item_removed_entirely_denies():
    bg = _load()
    r = bg.baseline_gate(baseline={"required_in_scope": ["A", "B"]}, feature_list=_fl("A"))
    assert r["deny"] is True and any("B" in x for x in r["reasons"])

def test_all_required_in_scope_passes():
    bg = _load()
    r = bg.baseline_gate(baseline={"required_in_scope": ["A", "B"]}, feature_list=_fl("A", "B"))
    assert r["deny"] is False

def test_malformed_inputs_fail_closed():
    bg = _load()
    assert bg.baseline_gate(baseline={"required_in_scope": ["A"]}, feature_list="x")["deny"] is True
    assert bg.baseline_gate(baseline={"required_in_scope": "A"}, feature_list=_fl("A"))["deny"] is True

def test_duplicate_id_ghost_bypass_is_denied():
    """Critical: an agent cannot satisfy RT-02 by adding a ghost in_scope:true duplicate
    of a real out-of-scope item. First-occurrence wins; the ghost must not satisfy the gate."""
    bg = _load()
    # Real item A is out-of-scope (first occurrence); ghost A is in_scope:true (second).
    fl = {"items": [
        {"id": "A", "in_scope": False},   # real item — out of scope
        {"id": "A", "in_scope": True},    # ghost — must be ignored (duplicate)
    ]}
    r = bg.baseline_gate(baseline={"required_in_scope": ["A"]}, feature_list=fl)
    assert r["deny"] is True, "ghost duplicate must not satisfy RT-02 gate"
