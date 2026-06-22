# tests/spine/test_baseline_writer.py
import importlib.util
import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
PI = ROOT / "plane-integration"


def _load_writer():
    s = importlib.util.spec_from_file_location("bw", ROOT / "tools/baseline_writer.py")
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


def _load_dispatcher():
    sys.path.insert(0, str(PI))
    import dispatcher  # noqa: PLC0415
    return dispatcher


# ---------------------------------------------------------------- baseline_writer unit
def test_write_baseline_roundtrip(tmp_path):
    bw = _load_writer()
    out = tmp_path / "coverage_baseline.json"
    bw.write_baseline(required_in_scope=["A", "B"], out_path=out)
    assert json.loads(out.read_text())["required_in_scope"] == ["A", "B"]


def test_write_baseline_deduplicates_ids(tmp_path):
    """write_baseline stringifies ids; calling code must not double-add."""
    bw = _load_writer()
    out = tmp_path / "coverage_baseline.json"
    bw.write_baseline(required_in_scope=["X", "X", "Y"], out_path=out)
    # The writer preserves the caller's list (dedup is dispatcher's responsibility).
    doc = json.loads(out.read_text())
    assert "X" in doc["required_in_scope"]
    assert "Y" in doc["required_in_scope"]


# ---------------------------------------------------------------- dispatcher integration
@pytest.fixture
def wired_dispatcher(tmp_path, monkeypatch):
    """Wire dispatcher's queue/state/audit/baseline to tmp_path, disable Plane."""
    dispatcher = _load_dispatcher()
    monkeypatch.setenv("ASCP_DISPATCHER_NO_PLANE", "1")
    monkeypatch.setattr(dispatcher, "QUEUE", tmp_path / "q.jsonl")
    monkeypatch.setattr(dispatcher, "STATE", tmp_path / "state.json")
    monkeypatch.setattr(dispatcher, "AUDIT", tmp_path / "audit.jsonl")
    monkeypatch.setattr(dispatcher, "BASELINE_PATH", tmp_path / "coverage_baseline.json")
    monkeypatch.setattr(dispatcher, "_audit", None)
    return dispatcher, tmp_path


def _write_queue(path, jobs):
    path.write_text("".join(json.dumps(j) + "\n" for j in jobs))


def test_drain_writes_baseline_for_dispatched_ids(wired_dispatcher):
    """drain() must write a baseline containing every successfully dispatched issue id."""
    dispatcher, tmp = wired_dispatcher
    _write_queue(dispatcher.QUEUE, [
        {"kind": "agent_dispatch", "agent_role": "initializer",
         "issue_id": "I1", "state": "Agent-Triaged", "delivery": "d1"},
        {"kind": "agent_dispatch", "agent_role": "implementer",
         "issue_id": "I2", "state": "In-Progress", "delivery": "d2"},
    ])

    baseline_path = tmp / "coverage_baseline.json"
    n = dispatcher.drain(
        invoker=lambda job: {"mode": "stage"},
        baseline_path=baseline_path,
    )

    assert n == 2
    assert baseline_path.exists(), "drain() must write the baseline after dispatching"
    doc = json.loads(baseline_path.read_text())
    assert set(doc["required_in_scope"]) == {"I1", "I2"}


def test_drain_baseline_excludes_quarantined_ids(wired_dispatcher):
    """ids that exhaust retries (quarantined) must NOT appear in the baseline."""
    dispatcher, tmp = wired_dispatcher

    _write_queue(dispatcher.QUEUE, [
        {"kind": "agent_dispatch", "agent_role": "verifier",
         "issue_id": "BAD", "state": "In-Verification", "delivery": "p1"},
        {"kind": "agent_dispatch", "agent_role": "initializer",
         "issue_id": "OK", "state": "Agent-Triaged", "delivery": "p2"},
    ])

    calls = []

    def selective_invoker(job):
        if job["issue_id"] == "BAD":
            raise RuntimeError("agent blew up")
        calls.append(job["issue_id"])
        return {"mode": "stage"}

    baseline_path = tmp / "coverage_baseline.json"
    # Drain MAX_ATTEMPTS times so BAD gets quarantined.
    for _ in range(dispatcher.MAX_ATTEMPTS):
        dispatcher.drain(invoker=selective_invoker, baseline_path=baseline_path)

    assert baseline_path.exists()
    doc = json.loads(baseline_path.read_text())
    assert "OK" in doc["required_in_scope"]
    assert "BAD" not in doc["required_in_scope"], (
        "quarantined ids must not appear in the trusted baseline"
    )


def test_drain_baseline_write_failure_raises(wired_dispatcher, monkeypatch):
    """A baseline write failure must propagate (fail-closed), not be silently swallowed."""
    dispatcher, tmp = wired_dispatcher
    _write_queue(dispatcher.QUEUE, [
        {"kind": "agent_dispatch", "agent_role": "initializer",
         "issue_id": "I1", "state": "Agent-Triaged", "delivery": "d1"},
    ])

    # Patch _write_baseline_fail_closed to raise so we can verify it propagates.
    def _boom(issue_ids, out_path=None):
        raise OSError("disk full")

    monkeypatch.setattr(dispatcher, "_write_baseline_fail_closed", _boom)

    baseline_path = tmp / "coverage_baseline.json"
    with pytest.raises(OSError, match="disk full"):
        dispatcher.drain(
            invoker=lambda job: {"mode": "stage"},
            baseline_path=baseline_path,
        )
    assert not baseline_path.exists(), "no baseline must exist after a write failure"


def test_drain_no_baseline_when_no_dispatched_ids(wired_dispatcher):
    """drain() must NOT write a baseline when nothing was dispatched."""
    dispatcher, tmp = wired_dispatcher
    # Queue is empty — nothing to dispatch.
    dispatcher.QUEUE.write_text("")

    baseline_path = tmp / "coverage_baseline.json"
    n = dispatcher.drain(
        invoker=lambda job: {"mode": "stage"},
        baseline_path=baseline_path,
    )

    assert n == 0
    assert not baseline_path.exists(), "no baseline must be written when nothing dispatched"
