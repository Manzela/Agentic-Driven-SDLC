"""Independent verifier for event_bus (REQ-ORCH / Phase 5 — Inngest steps).

These tests do NOT trust tools/event_bus.py — they exercise its public contract
directly and assert the three documented durable-bus behaviors:

  * emit() APPENDS to the durable, append-only log (length grows by one and the
    stored event is retrievable from the log).
  * run_step() executes a step's fn exactly ONCE per step_id; a second call with
    the SAME step_id returns the memoized result WITHOUT re-executing fn
    (call-counter == 1).
  * deliver() routes an event to its registered handler EXACTLY ONCE even when
    the same event is delivered twice (dedup by delivery id).
"""

from __future__ import annotations

import os
import sys

# Make the repo's tools/ package importable regardless of pytest's rootdir.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from tools.event_bus import EventBus


def test_emit_appends_to_the_log():
    bus = EventBus()
    assert len(bus.log) == 0

    stored = bus.emit({"name": "slice.proven", "data": {"slice": "S1"}})

    # The append is the durable act: exactly one entry now in the append-only log.
    log = bus.log
    assert len(log) == 1
    # The stored event carries the routing name and was assigned an id + ts.
    assert stored["name"] == "slice.proven"
    assert stored["id"]
    assert log[0]["id"] == stored["id"]
    assert log[0]["name"] == "slice.proven"

    # A second emit appends again — the log only grows, never shrinks/mutates.
    bus.emit({"name": "slice.failed", "data": {"slice": "S2"}})
    assert len(bus.log) == 2


def test_run_step_executes_once_and_memoizes():
    bus = EventBus()
    calls = {"n": 0}

    def step_fn():
        calls["n"] += 1
        return {"slice": "S1", "committed": True}

    # First call executes fn exactly once.
    r1 = bus.run_step("slice:S1:commit", step_fn)
    assert r1 == {"slice": "S1", "committed": True}
    assert calls["n"] == 1

    # Second call with the SAME step_id is a replay: memoized result, NO re-exec.
    r2 = bus.run_step("slice:S1:commit", step_fn)
    assert r2 == {"slice": "S1", "committed": True}
    assert calls["n"] == 1, "durable step must execute at most once per step_id"

    # A DIFFERENT step_id does execute its own fn (sanity: memoization is keyed).
    r3 = bus.run_step("slice:S2:commit", step_fn)
    assert r3 == {"slice": "S1", "committed": True}
    assert calls["n"] == 2, "a distinct step_id must run fn again"


def test_deliver_routes_once_even_if_delivered_twice():
    bus = EventBus()
    received = []

    def handler(event):
        received.append(event["id"])

    bus.on("slice.proven", handler)

    # Emit one event, deliver it.
    evt = bus.emit({"name": "slice.proven", "data": {"slice": "S1"}})
    first = bus.deliver()

    # Re-emit the SAME event id and re-drive deliver() (at-least-once redelivery,
    # e.g. a crash mid-dispatch causing the host to re-run deliver()).
    bus.emit({"name": "slice.proven", "id": evt["id"], "data": {"slice": "S1"}})
    second = bus.deliver()

    # The handler fired EXACTLY ONCE despite two deliveries (dedup by delivery_id).
    assert received == [evt["id"]]
    assert len(received) == 1

    # Receipts corroborate: first delivery delivered, the redelivery deduplicated.
    first_statuses = [r["status"] for r in first]
    second_statuses = [r["status"] for r in second]
    assert "delivered" in first_statuses
    assert second_statuses == ["deduplicated"], second_statuses


def test_deliver_skips_when_no_handler_registered():
    bus = EventBus()
    bus.emit({"name": "no.listeners", "data": {}})
    receipts = bus.deliver()
    assert [r["status"] for r in receipts] == ["skipped"]
