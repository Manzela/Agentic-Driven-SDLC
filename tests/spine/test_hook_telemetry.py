# tests/spine/test_hook_telemetry.py
import importlib.util, json, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[2]
def _load():
    spec = importlib.util.spec_from_file_location("ht", ROOT/"tools/hook_telemetry.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
def test_records_when_env_set(tmp_path, monkeypatch):
    sink = tmp_path/"fires.jsonl"; monkeypatch.setenv("SPINE_HOOK_TELEMETRY", str(sink))
    _load().record_fire("Stop", "s1", decision="block")
    rec = json.loads(sink.read_text().strip())
    assert rec["hook_event"]=="Stop" and rec["session_id"]=="s1" and rec["decision"]=="block"
def test_noop_when_unset(monkeypatch):
    monkeypatch.delenv("SPINE_HOOK_TELEMETRY", raising=False)
    _load().record_fire("Stop", "s1")   # must not raise
