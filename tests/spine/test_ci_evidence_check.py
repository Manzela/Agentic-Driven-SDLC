# tests/spine/test_ci_evidence_check.py
import importlib.util, hashlib, json, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[2]
def _load():
    spec = importlib.util.spec_from_file_location("cec", ROOT / "tools/ci_evidence_check.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
def test_rejects_hash_mismatch_at_ci(tmp_path):
    cec = _load()
    art = tmp_path / "arts"; art.mkdir()
    (art / "A.txt").write_text("real")
    h = "sha256:" + hashlib.sha256(b"FORGED").hexdigest()   # declared hash of different bytes
    fl = tmp_path / "feature_list.json"; fl.write_text(json.dumps({"items":[
        {"id":"A","in_scope":True,"status":"proven","evidence":{
            "test_file":"A.txt","test_name":"n","output_hash":h,
            "collected_at":"2026-06-22T00:00:00+00:00",
            "implementer_session_id":"i","verifier_session_id":"v"}}]}))
    led = tmp_path / "ledger.json"; led.write_text(json.dumps({"sessions":["i","v"]}))
    assert cec.run(feature_list_path=fl, artifacts_dir=art, ledger_path=led) == 1
def test_accepts_matching_hash(tmp_path):
    cec = _load()
    art = tmp_path / "arts"; art.mkdir(); (art / "A.txt").write_text("real")
    h = "sha256:" + hashlib.sha256(b"real").hexdigest()
    fl = tmp_path / "feature_list.json"; fl.write_text(json.dumps({"items":[
        {"id":"A","in_scope":True,"status":"proven","evidence":{
            "test_file":"A.txt","test_name":"n","output_hash":h,
            "collected_at":"2026-06-22T00:00:00+00:00",
            "implementer_session_id":"i","verifier_session_id":"v"}}]}))
    led = tmp_path / "ledger.json"; led.write_text(json.dumps({"sessions":["i","v"]}))
    assert cec.run(feature_list_path=fl, artifacts_dir=art, ledger_path=led) == 0
