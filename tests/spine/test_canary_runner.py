# tests/spine/test_canary_runner.py
import importlib.util, pathlib, pytest
ROOT = pathlib.Path(__file__).resolve().parents[2]
def _load():
    spec = importlib.util.spec_from_file_location("c", ROOT/"tools/run_spine_canary.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
def test_reinjection_detects_near_duplicates():
    c = _load()
    rows = [{"role":"user","content":"continue: 5 violations remain"},
            {"role":"user","content":"continue: 4 violations remain"}]  # near-dup
    with pytest.raises(AssertionError):
        c.assert_no_reinjection(rows, jaccard=0.9)
def test_all_hooks_fired_requires_full_set():
    c = _load()
    fires = [{"hook_event":e} for e in ["SessionStart","PreToolUse","Stop"]]
    with pytest.raises(AssertionError):
        c.assert_all_hooks_fired(fires, {"SessionStart","PreToolUse","PostToolUse","SubagentStop","Stop","PreCompact"})
def test_ralph_absent_flags_stop_hook_sh():
    c = _load()
    with pytest.raises(AssertionError):
        c.assert_ralph_absent([{"hook_event":"Stop","command_path":"/x/ralph-loop/stop-hook.sh"}])
