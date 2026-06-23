from __future__ import annotations

import importlib.util
import json
import pathlib
import stat

ROOT = pathlib.Path(__file__).resolve().parents[2]


def _load():
    spec = importlib.util.spec_from_file_location("ht", ROOT / "tools/hook_telemetry.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_records_when_env_set(tmp_path, monkeypatch):
    sink = tmp_path / "fires.jsonl"
    monkeypatch.setenv("SPINE_HOOK_TELEMETRY", str(sink))
    _load().record_fire("Stop", "s1", decision="block")
    rec = json.loads(sink.read_text().strip())
    assert rec["hook_event"] == "Stop"
    assert rec["session_id"] == "s1"
    assert rec["decision"] == "block"


def test_noop_when_unset(tmp_path, monkeypatch):
    monkeypatch.delenv("SPINE_HOOK_TELEMETRY", raising=False)
    _load().record_fire("Stop", "s1")  # must not raise
    # No file should exist in tmp_path — no side-effects anywhere.
    assert list(tmp_path.iterdir()) == [], "record_fire wrote a file when env var was unset"


def test_non_serializable_extra_does_not_raise(tmp_path, monkeypatch):
    """A non-JSON-serializable extra kwarg must be swallowed, not raised (wide except)."""
    sink = tmp_path / "fires.jsonl"
    monkeypatch.setenv("SPINE_HOOK_TELEMETRY", str(sink))
    _load().record_fire("Stop", "s1", bad=object())  # object() is not JSON-serialisable
    # The function must return without raising; the sink may or may not exist.


def test_oserror_on_readonly_dir(tmp_path, monkeypatch):
    """OSError on an unwritable sink dir must be swallowed silently (never raises)."""
    sink = tmp_path / "fires.jsonl"
    monkeypatch.setenv("SPINE_HOOK_TELEMETRY", str(sink))
    # Make the directory read-only so open(..., "a") raises OSError.
    tmp_path.chmod(stat.S_IRUSR | stat.S_IXUSR)
    try:
        _load().record_fire("Stop", "s1")  # must not raise
    finally:
        # Restore permissions so pytest can clean up tmp_path.
        tmp_path.chmod(stat.S_IRWXU)
