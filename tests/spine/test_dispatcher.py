"""Spine tests for the board→agent dispatcher (E6 consumer) + the webhook fail-closed fix.

Covers: only agent_dispatch jobs dispatch; unknown roles are blocked; dedup across drains;
poison-pill quarantine after MAX_ATTEMPTS; an audit row per processed job; and that the
webhook receiver is fail-closed when unconfigured.
"""
import json
import importlib
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
PI = ROOT / "plane-integration"
sys.path.insert(0, str(PI))

import dispatcher  # noqa: E402


@pytest.fixture
def wired(tmp_path, monkeypatch):
    """Point the dispatcher's queue/state/audit at a tmp dir and disable Plane write-back."""
    monkeypatch.setenv("ASCP_DISPATCHER_NO_PLANE", "1")
    monkeypatch.setattr(dispatcher, "QUEUE", tmp_path / "q.jsonl")
    monkeypatch.setattr(dispatcher, "STATE", tmp_path / "state.json")
    monkeypatch.setattr(dispatcher, "AUDIT", tmp_path / "audit.jsonl")
    monkeypatch.setattr(dispatcher, "_audit", None)  # reset cached AuditLog -> new tmp path
    return tmp_path


def _write_queue(path, jobs):
    path.write_text("".join(json.dumps(j) + "\n" for j in jobs))


def test_dispatches_only_valid_agent_jobs_and_dedups(wired, monkeypatch):
    calls = []
    monkeypatch.setattr(dispatcher, "default_invoker", lambda job: calls.append(job["issue_id"]) or {"mode": "stage"})

    _write_queue(dispatcher.QUEUE, [
        {"kind": "agent_dispatch", "agent_role": "initializer", "issue_id": "I1", "state": "Agent-Triaged", "delivery": "d1"},
        {"kind": "agent_dispatch", "agent_role": "wizard", "issue_id": "I2", "state": "X", "delivery": "d2"},  # bad role
        {"kind": "comment", "issue_id": "I3", "delivery": "d3"},  # not a dispatch
    ])

    n = dispatcher.drain(invoker=dispatcher.default_invoker)
    assert n == 1                      # only the valid dispatch ran
    assert calls == ["I1"]             # comment + unknown-role did not invoke
    # a second drain must NOT re-dispatch (dedup via persisted seen-set)
    assert dispatcher.drain(invoker=dispatcher.default_invoker) == 0
    assert calls == ["I1"]

    # an audit row was written for the allow (I1) and the block (I2 unknown role)
    rows = [json.loads(x) for x in dispatcher.AUDIT.read_text().splitlines() if x.strip()]
    decisions = {r.get("requirement_id", r.get("issue_id")): r["decision"] for r in rows}
    assert decisions.get("I1") == "allow"
    assert decisions.get("I2") == "block"


def test_poison_pill_is_quarantined_after_max_attempts(wired):
    _write_queue(dispatcher.QUEUE, [
        {"kind": "agent_dispatch", "agent_role": "verifier", "issue_id": "P1", "state": "In-Verification", "delivery": "p1"},
    ])

    def boom(_job):
        raise RuntimeError("agent blew up")

    # each drain re-reads the queue; the failing job is retried until quarantined
    for _ in range(dispatcher.MAX_ATTEMPTS):
        assert dispatcher.drain(invoker=boom) == 0
    # after MAX_ATTEMPTS the key is in `seen` (quarantined) and no longer retried
    st = json.loads(dispatcher.STATE.read_text())
    job_key = dispatcher.job_key({"delivery": "p1", "issue_id": "P1", "state": "In-Verification", "kind": "agent_dispatch"})
    assert job_key in st["seen"]
    assert job_key not in st["attempts"]


def test_empty_queue_is_safe(wired):
    assert dispatcher.drain(invoker=lambda j: {"mode": "stage"}) == 0


def test_webhook_verify_is_fail_closed(monkeypatch):
    import webhook_handler as wh
    importlib.reload(wh)

    # no secret + no dev flag => reject (fail-closed)
    monkeypatch.setattr(wh, "SECRET", "")
    monkeypatch.delenv("ASCP_DEV_ALLOW_UNSIGNED", raising=False)
    assert wh.verify("anything", b"payload") is False

    # explicit insecure dev opt-in => accept
    monkeypatch.setenv("ASCP_DEV_ALLOW_UNSIGNED", "1")
    assert wh.verify("", b"payload") is True

    # configured secret => only a correct HMAC passes
    monkeypatch.delenv("ASCP_DEV_ALLOW_UNSIGNED", raising=False)
    import hmac
    import hashlib
    monkeypatch.setattr(wh, "SECRET", "s3cr3t")
    raw = b'{"event":"issue"}'
    good = hmac.new(b"s3cr3t", raw, hashlib.sha256).hexdigest()
    assert wh.verify(good, raw) is True
    assert wh.verify("deadbeef", raw) is False
    assert wh.verify("", raw) is False
