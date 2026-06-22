# tests/spine/test_execution_bounds.py
import importlib, os


def test_thresholds_default_and_env_override(monkeypatch):
    import tools.execution_bounds as eb
    importlib.reload(eb)
    assert eb.MAX_TURNS_PER_SLICE == 25
    monkeypatch.setenv("SPINE_MAX_TURNS_PER_SLICE", "9")
    importlib.reload(eb)
    assert eb.MAX_TURNS_PER_SLICE == 9
