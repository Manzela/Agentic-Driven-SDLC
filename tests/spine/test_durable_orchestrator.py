"""Independent verifier for tools/durable_orchestrator.py.

REQ-ORCH (Phase 5 / Temporal-Inngest durable outer loop, requirements.md 15.2).

These tests do NOT trust the implementation's own assertions. They drive the
public contract directly and assert the four documented durable-execution
properties, each with an independent oracle:

  1. run_activity RETRIES up to max_attempts then HANDS OFF -- a permanently
     failing activity is invoked exactly max_attempts times (call-counter) and
     then raises Handoff; it NEVER loops forever.
  2. A SUCCESSFUL activity inside a workflow returns its value and records
     exactly ONE ACTIVITY_COMPLETED history event.
  3. REPLAYING a recorded history reproduces the identical result WITHOUT
     re-invoking the side-effecting activity (call-counter stays flat on replay).
  4. checkpoint -> resume ROUND-TRIPS the durable state (history + result) and a
     tamper of the blob is rejected.
"""

from __future__ import annotations

import os
import sys

import pytest

# Make the repo's tools/ package importable regardless of pytest's rootdir.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from tools.durable_orchestrator import (  # noqa: E402
    DurableWorkflow,
    EventType,
    Handoff,
    NonDeterminismError,
    RetryPolicy,
    checkpoint,
    resume,
    run_activity,
)


# ---------------------------------------------------------------------------
# 1. run_activity retries up to max_attempts, then raises Handoff.
# ---------------------------------------------------------------------------
def test_run_activity_retries_then_handoff() -> None:
    calls = {"n": 0}

    def always_fail() -> None:
        calls["n"] += 1
        raise RuntimeError("transient boom")

    policy = RetryPolicy(max_attempts=4)
    with pytest.raises(Handoff) as exc_info:
        run_activity(always_fail, retry_policy=policy, activity_name="boom")

    # Exactly max_attempts invocations -- 1 initial + 3 retries, never an
    # infinite loop.
    assert calls["n"] == 4, f"expected 4 invocations, got {calls['n']}"

    h = exc_info.value
    assert h.attempts == 4
    assert h.activity == "boom"
    assert isinstance(h.last_error, RuntimeError)
    # The underlying cause is chained for human audit.
    assert isinstance(exc_info.value.__cause__, RuntimeError)


def test_run_activity_retry_count_matches_policy() -> None:
    # A different budget must change the invocation count -- proving the cap is
    # honored, not hard-coded.
    for budget in (1, 2, 5):
        calls = {"n": 0}

        def boom() -> None:
            calls["n"] += 1
            raise ValueError("always")

        with pytest.raises(Handoff):
            run_activity(boom, retry_policy=RetryPolicy(max_attempts=budget))
        assert calls["n"] == budget, f"budget={budget} -> {calls['n']} calls"


# ---------------------------------------------------------------------------
# 2. A successful activity returns its value and records ONE history event.
# ---------------------------------------------------------------------------
def test_successful_activity_returns_value_and_records_one_event() -> None:
    calls = {"n": 0}

    def side_effect() -> str:
        calls["n"] += 1
        return "result-42"

    def body(wf: DurableWorkflow) -> str:
        return wf.run_activity(side_effect)

    wf = DurableWorkflow("wf-success")
    result = wf.execute(body)

    assert result == "result-42"
    assert calls["n"] == 1, "side effect must run exactly once on a fresh run"

    completed = [e for e in wf.history if e.type == EventType.ACTIVITY_COMPLETED]
    assert len(completed) == 1, f"expected 1 ACTIVITY_COMPLETED, got {len(completed)}"
    assert completed[0].payload == "result-42"


def test_run_activity_retries_then_succeeds() -> None:
    # Fails twice, succeeds on the third attempt -> returns the value, no handoff.
    calls = {"n": 0}

    def flaky() -> str:
        calls["n"] += 1
        if calls["n"] < 3:
            raise RuntimeError("transient")
        return "ok"

    out = run_activity(flaky, retry_policy=RetryPolicy(max_attempts=4))
    assert out == "ok"
    assert calls["n"] == 3, "1 initial + 2 retries"


# ---------------------------------------------------------------------------
# 3. Replaying a recorded history reproduces the SAME result WITHOUT
#    re-invoking the side-effecting activity (call-counter oracle).
# ---------------------------------------------------------------------------
def test_replay_does_not_reinvoke_side_effects() -> None:
    calls = {"n": 0}

    def side_effect() -> dict[str, int]:
        calls["n"] += 1
        return {"value": 7}

    def body(wf: DurableWorkflow) -> dict[str, object]:
        a = wf.run_activity(side_effect)
        t = wf.durable_timer("settle", 5)
        return {"activity": a, "timer": t}

    # First, live run: side effect runs once.
    wf1 = DurableWorkflow("wf-replay")
    out1 = wf1.execute(body)
    assert calls["n"] == 1, "fresh run invokes side effect once"

    # Replay against the SAME recorded history (new workflow seeded with history).
    calls_before_replay = calls["n"]
    wf2 = DurableWorkflow("wf-replay", history=list(wf1.history))
    out2 = wf2.execute(body)

    # Identical decision, ZERO re-invocations of the side effect.
    assert out2 == out1, "replay must reproduce the identical result"
    assert calls["n"] == calls_before_replay, (
        f"replay re-invoked the side effect: {calls['n']} != {calls_before_replay}"
    )


def test_replay_divergence_is_refused() -> None:
    # If the body requests a different activity on replay, the engine must refuse
    # rather than silently re-execute -- non-determinism safety.
    calls = {"a": 0, "b": 0}

    def act_a() -> int:
        calls["a"] += 1
        return 1

    def act_b() -> int:
        calls["b"] += 1
        return 2

    def body_a(wf: DurableWorkflow) -> int:
        return wf.run_activity(act_a, activity_name="A")

    def body_b(wf: DurableWorkflow) -> int:
        return wf.run_activity(act_b, activity_name="B")

    wf1 = DurableWorkflow("wf-diverge")
    wf1.execute(body_a)

    wf2 = DurableWorkflow("wf-diverge", history=list(wf1.history))
    with pytest.raises(NonDeterminismError):
        wf2.execute(body_b)
    # The divergent activity must never have run.
    assert calls["b"] == 0


# ---------------------------------------------------------------------------
# 4. checkpoint -> resume round-trips state.
# ---------------------------------------------------------------------------
def test_checkpoint_resume_round_trips_state() -> None:
    calls = {"n": 0}

    def side_effect() -> str:
        calls["n"] += 1
        return "durable-payload"

    def body(wf: DurableWorkflow) -> dict[str, object]:
        a = wf.run_activity(side_effect)
        t = wf.durable_timer("wait", 10)
        return {"a": a, "t": t}

    wf1 = DurableWorkflow("wf-ckpt")
    out1 = wf1.execute(body)
    assert calls["n"] == 1

    blob = checkpoint(wf1)
    assert isinstance(blob, str) and blob, "checkpoint must yield a non-empty blob"

    # Resume from the opaque blob, then replay: identical result, no side effect.
    calls_before = calls["n"]
    wf2 = resume(blob)
    assert isinstance(wf2, DurableWorkflow)
    assert wf2.workflow_id == "wf-ckpt"
    # The durable state survives the round-trip: re-checkpointing the resumed
    # workflow yields the byte-identical canonical blob (JSON has no tuple type,
    # so the canonical/durable form -- not the live in-memory repr -- is the
    # contract). Same event count and command payloads must be preserved.
    assert checkpoint(wf2) == blob, "resume->checkpoint must reproduce the blob"
    assert len(wf2.history) == len(wf1.history)
    activity_payloads = [
        e.payload for e in wf2.history if e.type == EventType.ACTIVITY_COMPLETED
    ]
    assert activity_payloads == ["durable-payload"]

    out2 = wf2.execute(body)
    assert out2 == out1, "resumed+replayed result must equal the original"
    assert calls["n"] == calls_before, "resume+replay must not re-run side effects"


def test_resume_rejects_tampered_blob() -> None:
    def side_effect() -> str:
        return "x"

    def body(wf: DurableWorkflow) -> str:
        return wf.run_activity(side_effect)

    wf1 = DurableWorkflow("wf-tamper")
    wf1.execute(body)
    blob = checkpoint(wf1)

    # Tamper with a recorded payload without fixing the integrity hash.
    tampered = blob.replace('"x"', '"forged"')
    assert tampered != blob, "tamper sentinel did not alter the blob"
    with pytest.raises(NonDeterminismError):
        resume(tampered)
