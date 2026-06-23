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
    row = json.loads((tmp_path / "run_state.json").read_text())
    assert row["no_progress_n"] == 0
    assert row["block_streak"] == 0


def test_block_streak_accumulates_and_resets(tmp_path):
    """block_streak increments only when no progress AND violation_count > 0."""
    d = _load()
    d.init(tmp_path, "s1")
    # no progress + violation → streak grows
    d.tick(tmp_path, made_progress=False, violation_count=2)
    d.tick(tmp_path, made_progress=False, violation_count=1)
    row = json.loads((tmp_path / "run_state.json").read_text())
    assert row["block_streak"] == 2
    # no progress + no violation → streak stays (no increment)
    d.tick(tmp_path, made_progress=False, violation_count=0)
    row = json.loads((tmp_path / "run_state.json").read_text())
    assert row["block_streak"] == 2
    # progress → streak resets
    d.tick(tmp_path, made_progress=True, violation_count=0)
    row = json.loads((tmp_path / "run_state.json").read_text())
    assert row["block_streak"] == 0


def test_tick_without_prior_init_creates_file(tmp_path):
    """tick() should fall back to init() when run_state.json is absent."""
    d = _load()
    assert not (tmp_path / "run_state.json").exists()
    row = d.tick(tmp_path, made_progress=True, violation_count=0)
    assert (tmp_path / "run_state.json").exists()
    assert row["iteration_count"] == 1
    assert row["session_id"] == "unknown"


def test_external_blocker_roundtrip(tmp_path):
    """external_blocker is written and cleared correctly."""
    d = _load()
    d.init(tmp_path, "s2")
    d.tick(tmp_path, made_progress=False, violation_count=0, external_blocker="waiting-for-ci")
    row = json.loads((tmp_path / "run_state.json").read_text())
    assert row["external_blocker"] == "waiting-for-ci"
    # clearing it
    d.tick(tmp_path, made_progress=True, violation_count=0, external_blocker=None)
    row = json.loads((tmp_path / "run_state.json").read_text())
    assert row["external_blocker"] is None


def test_budget_exceeded_roundtrip(tmp_path):
    """budget_exceeded is written by tick() and gates the HANDOFF path correctly."""
    d = _load()
    d.init(tmp_path, "s3")
    row = d.tick(tmp_path, made_progress=False, violation_count=0, budget_exceeded=True)
    assert row["budget_exceeded"] is True
    persisted = json.loads((tmp_path / "run_state.json").read_text())
    assert persisted["budget_exceeded"] is True
    # can be cleared again
    row = d.tick(tmp_path, made_progress=False, violation_count=0, budget_exceeded=False)
    assert row["budget_exceeded"] is False


def test_partial_json_on_disk_does_not_crash(tmp_path):
    """tick() must not KeyError when run_state.json exists but is missing iteration_count."""
    (tmp_path / "run_state.json").write_text(
        json.dumps({"session_id": "partial", "status": "running"})
    )
    d = _load()
    row = d.tick(tmp_path, made_progress=True, violation_count=0)
    # iteration_count defaulted to 0 then incremented → 1
    assert row["iteration_count"] == 1
    # no_progress_n and block_streak should both be 0 after a progress tick
    assert row["no_progress_n"] == 0
    assert row["block_streak"] == 0
