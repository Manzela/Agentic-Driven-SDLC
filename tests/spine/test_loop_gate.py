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


# --- Task 5: depth-pillar wiring in gated_advance (§4.3) ----------------------
# Depth checks are monkeypatched on lg.evidence_gate — the SAME canonical module
# object gated_advance dereferences (`from tools import evidence_gate`). Patching a
# separately _load()-ed instance would NOT intercept the call (fresh module each load).
_REJECT_SAST = {"accepted": False, "code": "SAST_HIGH_CRITICAL", "reason": "semgrep found 1 HIGH issue"}
_REJECT_ORPH = {"accepted": False, "code": "ORPHAN_DETECTED", "reason": "found unmatched references"}
_ACCEPT = {"accepted": True, "code": "OK", "reason": ""}


def test_depth_codes_and_funcs_reachable():
    """The depth codes + heal prompts + functions are reachable through the gate's
    evidence_gate (Task-4 deliverables wired in; not re-stubbed)."""
    lg = _load("tools/loop_gate.py", "lg")
    eg = lg.evidence_gate
    for code in ("SAST_HIGH_CRITICAL", "ORPHAN_DETECTED", "ORPHAN_DANGLING_REF"):
        assert code in eg.CODES
        assert eg.self_heal_prompt({"code": code}) not in ("", None)
    assert callable(eg.check_slice_semgrep)
    assert callable(eg.check_slice_orphans)


def test_gated_advance_accepts_depth_kwargs_backward_compat(tmp_path):
    """Old call shape still advances; new depth kwargs are accepted without error."""
    lg = _load("tools/loop_gate.py", "lg")
    rsd = _load("tools/run_state_driver.py", "rsd"); rsd.init(tmp_path, "s")
    r = lg.gated_advance(root=tmp_path, evidence=_ev(), artifact=ART, ledger=LEDGER)
    assert r["action"] == "advance"
    r2 = lg.gated_advance(root=tmp_path, evidence=_ev(), artifact=ART, ledger=LEDGER,
                          changed_files=[], baseline_commit="abc",
                          feature_list_path=None, known_ids=set())
    assert r2["action"] == "advance"


def test_pillar0_reject_blocks_depth_checks(tmp_path, monkeypatch):
    """Pillar 0 (fail-CLOSED) reject escalates WITHOUT running either depth pillar —
    a fail-open 'accept' must never get a vote once the trust core has rejected."""
    lg = _load("tools/loop_gate.py", "lg")
    rsd = _load("tools/run_state_driver.py", "rsd"); rsd.init(tmp_path, "s")
    calls = {"semgrep": 0, "orphans": 0}

    def _track_semgrep(*a, **k): calls["semgrep"] += 1; return _ACCEPT
    def _track_orphans(*a, **k): calls["orphans"] += 1; return _ACCEPT
    monkeypatch.setattr(lg.evidence_gate, "check_slice_semgrep", _track_semgrep)
    monkeypatch.setattr(lg.evidence_gate, "check_slice_orphans", _track_orphans)

    r = lg.gated_advance(root=tmp_path, evidence=_ev(verifier_session_id="i"),
                         artifact=ART, ledger=LEDGER, changed_files=["test.py"],
                         baseline_commit="abc")
    assert r["code"] == "SAME_SESSION"
    assert calls["semgrep"] == 0 and calls["orphans"] == 0


def test_pillar1_semgrep_rejection_self_heals(tmp_path, monkeypatch):
    lg = _load("tools/loop_gate.py", "lg")
    rsd = _load("tools/run_state_driver.py", "rsd"); rsd.init(tmp_path, "s")
    monkeypatch.setattr(lg.evidence_gate, "check_slice_semgrep", lambda *a, **k: _REJECT_SAST)
    monkeypatch.setattr(lg.evidence_gate, "check_slice_orphans", lambda *a, **k: _ACCEPT)
    r = lg.gated_advance(root=tmp_path, evidence=_ev(), artifact=ART, ledger=LEDGER,
                         changed_files=["test.py"], baseline_commit="abc", max_self_heal=2)
    assert r["action"] == "self_heal"
    assert r["code"] == "SAST_HIGH_CRITICAL"
    assert "semgrep" in r["prompt"].lower()
    assert r["run_state"]["block_streak"] == 1


def test_pillar2_orphan_rejection_self_heals(tmp_path, monkeypatch):
    lg = _load("tools/loop_gate.py", "lg")
    rsd = _load("tools/run_state_driver.py", "rsd"); rsd.init(tmp_path, "s")
    monkeypatch.setattr(lg.evidence_gate, "check_slice_semgrep", lambda *a, **k: _ACCEPT)
    monkeypatch.setattr(lg.evidence_gate, "check_slice_orphans", lambda *a, **k: _REJECT_ORPH)
    r = lg.gated_advance(root=tmp_path, evidence=_ev(), artifact=ART, ledger=LEDGER,
                         changed_files=["test.py"], feature_list_path="/tmp/feature_list.json",
                         known_ids=set(), max_self_heal=2)
    assert r["action"] == "self_heal"
    assert r["code"] == "ORPHAN_DETECTED"
    assert "orphan" in r["prompt"].lower() or "requirement" in r["prompt"].lower()
    assert r["run_state"]["block_streak"] == 1


def test_dual_pillar_rejection_joins_prompts(tmp_path, monkeypatch):
    """Both pillars reject → both reasons AND both heal-prompts appear in one self_heal."""
    lg = _load("tools/loop_gate.py", "lg")
    rsd = _load("tools/run_state_driver.py", "rsd"); rsd.init(tmp_path, "s")
    monkeypatch.setattr(lg.evidence_gate, "check_slice_semgrep", lambda *a, **k: _REJECT_SAST)
    monkeypatch.setattr(lg.evidence_gate, "check_slice_orphans", lambda *a, **k: _REJECT_ORPH)
    r = lg.gated_advance(root=tmp_path, evidence=_ev(), artifact=ART, ledger=LEDGER,
                         changed_files=["test.py"], baseline_commit="abc",
                         feature_list_path="/tmp/feature_list.json", known_ids=set(), max_self_heal=2)
    assert r["action"] == "self_heal"
    assert "semgrep found 1 HIGH issue" in r["reason"]
    assert "found unmatched references" in r["reason"]
    assert "semgrep" in r["prompt"].lower()
    assert "orphan" in r["prompt"].lower() or "requirement" in r["prompt"].lower()
    assert r["code"] == "SAST_HIGH_CRITICAL"  # first-rejected pillar (semgrep before orphans)
    # F4 (red-team): the joined prompt orders semgrep before the orphan heal text too
    assert r["prompt"].lower().index("semgrep") < r["prompt"].lower().index("orphan")


def test_empty_changed_files_skips_depth_checks(tmp_path, monkeypatch):
    lg = _load("tools/loop_gate.py", "lg")
    rsd = _load("tools/run_state_driver.py", "rsd"); rsd.init(tmp_path, "s")
    calls = {"n": 0}
    def _track(*a, **k): calls["n"] += 1; return _ACCEPT
    monkeypatch.setattr(lg.evidence_gate, "check_slice_semgrep", _track)
    monkeypatch.setattr(lg.evidence_gate, "check_slice_orphans", _track)
    r = lg.gated_advance(root=tmp_path, evidence=_ev(), artifact=ART, ledger=LEDGER, changed_files=[])
    assert r["action"] == "advance"
    assert calls["n"] == 0


def test_orphan_pillar_skipped_when_no_feature_list_path(tmp_path, monkeypatch):
    """F1 (red-team): without a feature_list_path the orphan pillar is EXPLICITLY
    skipped (not invoked with '' -> IsADirectoryError -> silent fail-open-forever)."""
    lg = _load("tools/loop_gate.py", "lg")
    rsd = _load("tools/run_state_driver.py", "rsd"); rsd.init(tmp_path, "s")
    orph_calls = {"n": 0}
    def _track_orph(*a, **k): orph_calls["n"] += 1; return _ACCEPT
    monkeypatch.setattr(lg.evidence_gate, "check_slice_semgrep", lambda *a, **k: _ACCEPT)
    monkeypatch.setattr(lg.evidence_gate, "check_slice_orphans", _track_orph)
    r = lg.gated_advance(root=tmp_path, evidence=_ev(), artifact=ART, ledger=LEDGER,
                         changed_files=["x.py"])  # no feature_list_path
    assert r["action"] == "advance"
    assert orph_calls["n"] == 0  # orphan pillar NOT called without a path


def test_bare_string_changed_files_normalized_to_list(tmp_path, monkeypatch):
    """F2 (red-team): a bare path string is normalized to a one-element list before
    reaching the pillars (no per-character iteration)."""
    lg = _load("tools/loop_gate.py", "lg")
    rsd = _load("tools/run_state_driver.py", "rsd"); rsd.init(tmp_path, "s")
    seen = {}
    def _capture(*a, **k): seen["changed_files"] = k.get("changed_files"); return _ACCEPT
    monkeypatch.setattr(lg.evidence_gate, "check_slice_semgrep", _capture)
    monkeypatch.setattr(lg.evidence_gate, "check_slice_orphans", lambda *a, **k: _ACCEPT)
    lg.gated_advance(root=tmp_path, evidence=_ev(), artifact=ART, ledger=LEDGER,
                     changed_files="mod.py")
    assert seen["changed_files"] == ["mod.py"]


def test_depth_block_streak_handoff_escalation(tmp_path, monkeypatch):
    """A persistent depth reject self-heals then converts to HANDOFF at the bound
    (>=, consistent with the Pillar-0 path: max_self_heal=2 → call2 handoffs)."""
    lg = _load("tools/loop_gate.py", "lg")
    rsd = _load("tools/run_state_driver.py", "rsd"); rsd.init(tmp_path, "s")
    monkeypatch.setattr(lg.evidence_gate, "check_slice_semgrep", lambda *a, **k: _REJECT_SAST)
    monkeypatch.setattr(lg.evidence_gate, "check_slice_orphans", lambda *a, **k: _ACCEPT)
    kw = dict(root=tmp_path, evidence=_ev(), artifact=ART, ledger=LEDGER,
              changed_files=["x.py"], baseline_commit="abc", max_self_heal=2)
    r1 = lg.gated_advance(**kw)
    assert r1["action"] == "self_heal" and r1["run_state"]["block_streak"] == 1
    r2 = lg.gated_advance(**kw)
    assert r2["action"] == "handoff" and r2["run_state"]["block_streak"] == 2
    assert "escalating to HANDOFF" in r2["reason"]
