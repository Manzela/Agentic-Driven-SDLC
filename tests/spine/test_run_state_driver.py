"""tests/spine/test_run_state_driver.py — file-backed run_state populator (Task 9)."""
from __future__ import annotations

import importlib.util
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]


def _load():
    spec = importlib.util.spec_from_file_location("rsd", ROOT / "tools/run_state_driver.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_init_and_tick_persist(tmp_path):
    d = _load()
    d.init(tmp_path, "s1")
    assert json.loads((tmp_path / "run_state.json").read_text())["iteration_count"] == 0
    d.tick(tmp_path, made_progress=False, violation_count=1)
    d.tick(tmp_path, made_progress=False, violation_count=1)
    row = json.loads((tmp_path / "run_state.json").read_text())
    assert row["iteration_count"] == 2
    assert row["no_progress_n"] == 2


def test_progress_resets_streak(tmp_path):
    d = _load()
    d.init(tmp_path, "s1")
    d.tick(tmp_path, made_progress=False, violation_count=0)
    d.tick(tmp_path, made_progress=True, violation_count=0)
    assert json.loads((tmp_path / "run_state.json").read_text())["no_progress_n"] == 0
