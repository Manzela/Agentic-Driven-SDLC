"""event_bus.py — Inngest-style event-driven DURABLE STEP bus (reference).

Spec: .kiro/specs/spec-to-evidence-control/tasks.md, tasks 43 / 43.1
Requirements: Requirement 15 (Orchestration) — REQ-ORCH-001..003 / 15.2
Phase: 5 (OPTIONAL) — Temporal/Inngest durable outer loop.

This is the pure-Python reference model for the **Phase-5 optional** durable
outer loop. The governing invariant of the control plane is unchanged: this bus
is OFF the delivery-gating path (Requirement 15.1 keeps the inner planner /
implementer / verifier loop on Claude Code's own subagents + hooks; durability
is added "only when truly needed"). Nothing in this module decides whether a
deliverable is COMPLETE — deterministic gates (hooks / OPA / CI) still own that.
What this module DOES provide is the crash-safe scaffolding that Requirement
15.2 calls for: "wrap the loop in Temporal_Inngest invoking ``claude -p`` as a
durable step, with each tool call as a separate activity."

The four primitives modelled here mirror the Inngest execution semantics:

  * ``EventBus.emit(event)``        — append-only event log (the durable record
                                      of every trigger; nothing is mutated or
                                      deleted, only appended).
  * ``EventBus.on(name, handler)``  — register a handler (an Inngest "function")
                                      that fires when a matching event is
                                      delivered.
  * ``EventBus.run_step(id, fn)``   — a DURABLE STEP: ``fn`` runs at most once
                                      per ``step_id``; on a replay (re-run after
                                      a crash) the MEMOIZED result is returned
                                      WITHOUT re-executing ``fn``. This is the
                                      idempotency guarantee that lets a durable
                                      workflow resume from where it crashed
                                      instead of repeating side effects.
  * ``EventBus.deliver()``          — dispatch queued events to their handlers
                                      with AT-LEAST-ONCE semantics, de-duplicated
                                      by a per-(delivery, handler) delivery id so
                                      a redelivered event is processed exactly
                                      once by each handler.

Durability boundary: ``run_step`` memoization and the delivery-dedup ledger are
the two pieces of state that must survive a crash for "exactly-once effects"
to hold on top of "at-least-once delivery". Both are held in plain dicts here
and exposed via ``snapshot()`` / ``restore()`` so a host (Temporal/Inngest, or a
test) can persist them to durable storage and rehydrate on resume. Replaying the
same event log against a restored bus reproduces the same observable effects.

This module is PURE STDLIB and has no Temporal/Inngest dependency — it is the
*reference semantics* the optional engine would provide, usable directly in
tests and as a local, dependency-free durable stub behind the Phase-5 flag.
"""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

__all__ = [
    "Event",
    "Handler",
    "EventBus",
    "DurableStepError",
    "new_event_id",
    "utc_now",
]

# An Event is a plain dict so it round-trips through JSON / a durable store /
# a process boundary with no custom (de)serialization — same discipline as the
# Evidence_Record contract in evidence_collector.py.
Event = Dict[str, Any]

# A Handler receives the delivered event dict and may return anything. Its return
# value is ignored by ``deliver`` (handlers act via side effects, like Inngest
# functions); raised exceptions surface to the caller of ``deliver``.
Handler = Callable[[Event], Any]


class DurableStepError(RuntimeError):
    """Raised when a durable-step invariant is violated.

    The only invariant a *caller* can violate is re-running the same
    ``step_id`` with a function whose recorded outcome was an ERROR while not
    asking to re-raise — but for ergonomics the default replay behaviour is to
    re-raise the memoized error, so this type is mainly a marker for the
    "step recorded no terminal outcome" corruption case during ``restore``.
    """


def utc_now() -> str:
    """Return an RFC-3339 / ISO-8601 timezone-aware UTC timestamp string.

    Matches the timestamp shape used elsewhere in the control plane
    (evidence_collector.collect, audit_log) so event records line up with the
    rest of the durable record set.
    """
    return datetime.now(timezone.utc).isoformat()


# Monotonic, process-local sequence used only to make auto-generated event ids
# unique and ordered within a single process. The durable identity of an event
# is its ``id`` field; callers may supply their own deterministic id (e.g. a
# content hash) to make ``emit`` itself idempotent across replays.
_SEQ_LOCK = threading.Lock()
_SEQ = 0


def new_event_id() -> str:
    """Generate a process-unique, ordered event id (``evt-<n>``)."""
    global _SEQ
    with _SEQ_LOCK:
        _SEQ += 1
        n = _SEQ
    return f"evt-{n:012d}"


class EventBus:
    """An append-only, durable-step event bus with at-least-once delivery.

    The bus owns four pieces of state:

      * ``_log``       — the append-only event log (ordered list of events).
      * ``_handlers``  — ``event_name -> [Handler, ...]`` registrations.
      * ``_steps``     — ``step_id -> StepRecord`` memoization ledger; the heart
                         of durable-step idempotency.
      * ``_delivered`` — set of ``delivery_id`` strings already processed; the
                         dedup ledger that turns at-least-once into
                         effectively-once per handler.

    All public methods are thread-safe (a single re-entrant lock guards the
    state); handlers run OUTSIDE the lock so a handler may itself call
    ``run_step`` / ``emit`` without deadlocking.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._log: List[Event] = []
        self._handlers: Dict[str, List[Handler]] = {}
        # step_id -> {"status": "ok"|"error", "value": <json-ish>, "error": str,
        #             "recorded_at": <ts>}
        self._steps: Dict[str, Dict[str, Any]] = {}
        # delivery_id -> recorded_at (presence == already delivered to a handler)
        self._delivered: Dict[str, str] = {}
        # FIFO of (event_index) not-yet-dispatched events. We store indexes into
        # ``_log`` so the queue never duplicates the durable event payload.
        self._queue: List[int] = []

    # ------------------------------------------------------------------ emit --
    def emit(self, event: Event) -> Event:
        """Append ``event`` to the durable log and enqueue it for delivery.

        The append is the durable act: the log is **append-only**, never
        mutated or compacted in place (the same discipline the gate_audit_log
        hash chain follows — design.md "mid-chain pruning is prohibited").

        ``event`` MUST be a dict and MUST carry a ``name`` (the routing key
        handlers register against). If it lacks an ``id``, a process-unique one
        is assigned; if it lacks a ``ts``, an emit timestamp is stamped. The
        stored event is a shallow copy so the caller's dict is not mutated and
        the log entry cannot be aliased/changed after the fact.

        Re-emitting an event whose ``id`` already exists in the log is treated
        as an idempotent no-op on the LOG (the existing entry is returned) but
        the event is still enqueued for delivery — delivery-level dedup
        (``delivery_id``) is what prevents a handler from running twice. This
        lets a crash-replay safely re-drive ``emit`` for the same logical event.

        Returns the stored (canonicalized) event dict.
        """
        if not isinstance(event, dict):
            raise TypeError("event must be a dict")
        name = event.get("name")
        if not name or not isinstance(name, str):
            raise ValueError("event must carry a non-empty string 'name'")

        with self._lock:
            stored = dict(event)  # shallow copy — do not alias caller's dict
            stored.setdefault("id", new_event_id())
            stored.setdefault("ts", utc_now())
            event_id = stored["id"]

            existing_index = self._index_of(event_id)
            if existing_index is None:
                self._log.append(stored)
                index = len(self._log) - 1
            else:
                # Idempotent re-emit: keep the original durable record, but still
                # schedule a delivery attempt (dedup happens at deliver time).
                stored = self._log[existing_index]
                index = existing_index

            self._queue.append(index)
            return dict(stored)

    def _index_of(self, event_id: str) -> Optional[int]:
        for i, e in enumerate(self._log):
            if e.get("id") == event_id:
                return i
        return None

    # -------------------------------------------------------------------- on --
    def on(self, event_name: str, handler: Handler) -> Callable[[], None]:
        """Register ``handler`` to fire when an event named ``event_name`` is
        delivered. Multiple handlers may register for the same name; each is an
        independent Inngest-style "function" and gets its own delivery-dedup id.

        Returns an ``unsubscribe()`` callable that removes this exact handler.
        Registration is idempotent for the same (name, handler) pair — the same
        handler object is not added twice.
        """
        if not event_name or not isinstance(event_name, str):
            raise ValueError("event_name must be a non-empty string")
        if not callable(handler):
            raise TypeError("handler must be callable")
        with self._lock:
            handlers = self._handlers.setdefault(event_name, [])
            if handler not in handlers:
                handlers.append(handler)

        def unsubscribe() -> None:
            with self._lock:
                hs = self._handlers.get(event_name, [])
                if handler in hs:
                    hs.remove(handler)

        return unsubscribe

    # ------------------------------------------------------------- run_step --
    def run_step(self, step_id: str, fn: Callable[[], Any]) -> Any:
        """Execute ``fn`` durably, MEMOIZED by ``step_id`` (idempotent step).

        This is the core Inngest durable-step guarantee (Requirement 15.2 —
        "``claude -p`` as a durable step, each tool call as a separate
        activity"):

          * The FIRST call for a given ``step_id`` runs ``fn`` exactly once and
            records its terminal outcome (the return value, or the raised
            exception) in the durable step ledger.
          * Any LATER call with the SAME ``step_id`` — i.e. a REPLAY after a
            crash/resume — returns the cached result WITHOUT re-executing
            ``fn``. If the first run raised, the replay re-raises an equivalent
            error rather than silently swallowing it, so control flow on replay
            matches the original run.

        Because the result must survive a crash and round-trip through durable
        storage, ``fn``'s return value SHOULD be JSON-serializable. This is
        enforced defensively: a non-serializable value is rejected (so a step
        cannot record a result that could not be restored on resume), keeping
        the live ledger and any restored ledger byte-identical.

        ``fn`` takes no arguments — bind its inputs with a closure/partial at the
        call site (exactly how an Inngest ``step.run("id", lambda: ...)`` is
        written). ``step_id`` MUST be unique per logical step within a run;
        reusing an id for a DIFFERENT computation is the caller's bug and will
        (correctly) return the first computation's memoized result.
        """
        if not step_id or not isinstance(step_id, str):
            raise ValueError("step_id must be a non-empty string")
        if not callable(fn):
            raise TypeError("fn must be callable")

        # Fast path: already recorded -> replay from the ledger, no execution.
        with self._lock:
            record = self._steps.get(step_id)
        if record is not None:
            return self._replay(step_id, record)

        # Execute OUTSIDE the lock (fn may itself call run_step/emit).
        try:
            value = fn()
        except Exception as exc:  # noqa: BLE001 — durable steps record any error
            err_repr = f"{type(exc).__name__}: {exc}"
            with self._lock:
                # Honour a race: if a concurrent caller already recorded this
                # step, defer to that record instead of overwriting it.
                existing = self._steps.get(step_id)
                if existing is None:
                    self._steps[step_id] = {
                        "status": "error",
                        "value": None,
                        "error": err_repr,
                        "recorded_at": utc_now(),
                    }
                    record = self._steps[step_id]
                else:
                    record = existing
            return self._replay(step_id, record)

        # Reject results that could not survive a durable round-trip, so the
        # in-memory ledger and a restored ledger can never diverge.
        try:
            json.dumps(value)
        except (TypeError, ValueError) as exc:
            raise DurableStepError(
                f"step {step_id!r} returned a non-JSON-serializable result "
                f"({type(value).__name__}); durable steps must return "
                f"JSON-serializable values: {exc}"
            ) from exc

        with self._lock:
            existing = self._steps.get(step_id)
            if existing is None:
                self._steps[step_id] = {
                    "status": "ok",
                    "value": value,
                    "error": None,
                    "recorded_at": utc_now(),
                }
                record = self._steps[step_id]
            else:
                # Lost the race: a concurrent caller recorded first. Return the
                # winning record so all callers observe the SAME memoized value.
                record = existing
        return self._replay(step_id, record)

    @staticmethod
    def _replay(step_id: str, record: Dict[str, Any]) -> Any:
        """Return the memoized outcome of a step, re-raising a recorded error."""
        status = record.get("status")
        if status == "ok":
            # Hand back a deep-ish copy for container types so a caller mutating
            # the returned value cannot corrupt the durable ledger entry.
            return _clone(record.get("value"))
        if status == "error":
            raise RuntimeError(
                f"durable step {step_id!r} previously failed and is being "
                f"replayed: {record.get('error')}"
            )
        raise DurableStepError(
            f"durable step {step_id!r} has a corrupt ledger record (no terminal "
            f"status): {record!r}"
        )

    def has_step(self, step_id: str) -> bool:
        """True iff ``step_id`` has a memoized terminal outcome."""
        with self._lock:
            return step_id in self._steps

    # ------------------------------------------------------------- deliver --
    def deliver(self) -> List[Dict[str, Any]]:
        """Dispatch all queued events to their handlers (AT-LEAST-ONCE + dedup).

        Semantics, matching Inngest's delivery model:

          * Every queued event is delivered to EACH handler registered for its
            ``name``. Delivery is AT-LEAST-ONCE: a redelivery of the same event
            (e.g. a crash mid-dispatch causing the host to re-drive ``deliver``)
            is safe.
          * Each (event, handler) pair has a stable ``delivery_id`` =
            ``"<event_id>:<handler_key>"``. Before invoking a handler, the bus
            checks the dedup ledger; if that ``delivery_id`` was already
            processed, the handler is SKIPPED. This turns at-least-once delivery
            into effectively-once EFFECTS per handler — the standard
            "at-least-once + idempotency-key" pattern.
          * The dedup mark is written ONLY after the handler returns
            successfully. If a handler RAISES, the delivery is NOT marked done,
            so a subsequent ``deliver`` will retry it (at-least-once retry on
            failure). To keep failures visible and ordering intact, the first
            handler exception aborts the current ``deliver`` call and the
            offending delivery stays unmarked, hence eligible for retry.

        Returns a list of per-delivery receipts (one dict per (event, handler)
        pair that was *attempted* in this call), each:
            {"event_id", "name", "handler", "delivery_id", "status"}
        where ``status`` is ``"delivered"``, ``"deduplicated"``, or ``"skipped"``
        (no handler registered for the event name).
        """
        receipts: List[Dict[str, Any]] = []

        while True:
            with self._lock:
                if not self._queue:
                    break
                index = self._queue.pop(0)
                event = self._log[index]
                name = event.get("name", "")
                event_id = event.get("id", "")
                handlers = list(self._handlers.get(name, []))

            if not handlers:
                # Nothing registered — record a skip receipt but still consider
                # the event "seen". (It remains in the durable log forever.)
                receipts.append({
                    "event_id": event_id,
                    "name": name,
                    "handler": None,
                    "delivery_id": None,
                    "status": "skipped",
                })
                continue

            for handler in handlers:
                handler_key = _handler_key(handler)
                delivery_id = f"{event_id}:{handler_key}"

                with self._lock:
                    already = delivery_id in self._delivered
                if already:
                    receipts.append({
                        "event_id": event_id,
                        "name": name,
                        "handler": handler_key,
                        "delivery_id": delivery_id,
                        "status": "deduplicated",
                    })
                    continue

                # Invoke OUTSIDE the lock; mark done only on success so a raising
                # handler is retried on the next deliver() (at-least-once).
                handler(dict(event))  # hand the handler its own copy
                with self._lock:
                    self._delivered[delivery_id] = utc_now()
                receipts.append({
                    "event_id": event_id,
                    "name": name,
                    "handler": handler_key,
                    "delivery_id": delivery_id,
                    "status": "delivered",
                })

        return receipts

    # ----------------------------------------------------------- inspection --
    @property
    def log(self) -> List[Event]:
        """A copy of the append-only event log (read-only view)."""
        with self._lock:
            return [dict(e) for e in self._log]

    def pending(self) -> int:
        """Number of events enqueued but not yet dispatched by ``deliver``."""
        with self._lock:
            return len(self._queue)

    def delivered_ids(self) -> List[str]:
        """The set of delivery ids already processed (dedup ledger keys)."""
        with self._lock:
            return sorted(self._delivered.keys())

    # ------------------------------------------------- durability snapshot --
    def snapshot(self) -> Dict[str, Any]:
        """Serialize the crash-relevant state to a JSON-able dict.

        A host (Temporal/Inngest, or a test harness) persists this to durable
        storage; on resume it rehydrates with ``restore`` and replays the event
        log. The step ledger and the delivery-dedup ledger are exactly the two
        structures that must survive a crash for effects to remain
        effectively-once across a replay.
        """
        with self._lock:
            return {
                "log": [dict(e) for e in self._log],
                "queue": list(self._queue),
                "steps": {k: dict(v) for k, v in self._steps.items()},
                "delivered": dict(self._delivered),
            }

    @classmethod
    def restore(cls, state: Dict[str, Any]) -> "EventBus":
        """Rebuild a bus from a ``snapshot`` dict.

        Handlers are NOT part of the snapshot (they are code, not state) — the
        host re-registers them with ``on`` before re-driving ``deliver``. The
        restored bus has the same durable identity, so re-emitting the same
        events and re-running the same ``step_id``s reproduces the same effects.
        """
        bus = cls()
        with bus._lock:
            bus._log = [dict(e) for e in state.get("log", [])]
            bus._queue = list(state.get("queue", []))
            steps = state.get("steps", {})
            for sid, rec in steps.items():
                if "status" not in rec:
                    raise DurableStepError(
                        f"restored step {sid!r} has no terminal status: {rec!r}"
                    )
            bus._steps = {k: dict(v) for k, v in steps.items()}
            bus._delivered = dict(state.get("delivered", {}))
        return bus


def _handler_key(handler: Handler) -> str:
    """Stable, human-readable key for a handler used in the dedup ledger.

    Prefers ``__qualname__`` so two distinct functions get distinct keys; falls
    back to ``repr``. The key is part of the durable ``delivery_id``, so it must
    be stable across a process for the same logical handler.
    """
    name = getattr(handler, "__qualname__", None) or getattr(handler, "__name__", None)
    if name:
        module = getattr(handler, "__module__", "") or ""
        return f"{module}.{name}" if module else name
    return repr(handler)


def _clone(value: Any) -> Any:
    """Defensive copy of a memoized value via a JSON round-trip.

    Step results are required to be JSON-serializable (enforced in ``run_step``),
    so a JSON round-trip is a cheap deep copy that also guarantees the returned
    object shares no mutable structure with the durable ledger entry. Immutable
    scalars are returned as-is.
    """
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return json.loads(json.dumps(value))


# --------------------------------------------------------------------------- #
# Self-demonstration: a tiny durable workflow showing memoized steps,          #
# at-least-once delivery with dedup, and snapshot/restore replay.              #
# Run:  python tools/event_bus.py                                              #
# --------------------------------------------------------------------------- #
if __name__ == "__main__":  # pragma: no cover - illustrative, not a test
    bus = EventBus()

    _executions = {"slice": 0}

    def _run_slice() -> dict:
        _executions["slice"] += 1
        return {"slice": "S1", "committed": True}

    # First run executes; replay (same step_id) returns the memoized result.
    r1 = bus.run_step("slice:S1", _run_slice)
    r2 = bus.run_step("slice:S1", _run_slice)
    assert r1 == r2 == {"slice": "S1", "committed": True}
    assert _executions["slice"] == 1, "durable step must execute at most once"

    _received: list = []
    bus.on("slice.proven", lambda e: _received.append(e["id"]))

    e = bus.emit({"name": "slice.proven", "data": {"slice": "S1"}})
    first = bus.deliver()
    # Re-emit the SAME event id + redeliver: handler must NOT fire twice.
    bus.emit({"name": "slice.proven", "id": e["id"], "data": {"slice": "S1"}})
    second = bus.deliver()
    assert len(_received) == 1, "at-least-once delivery must dedup by delivery_id"

    # Snapshot -> restore -> replay reproduces the same memoized step result.
    snap = bus.snapshot()
    restored = EventBus.restore(snap)
    r3 = restored.run_step("slice:S1", _run_slice)
    assert r3 == r1, "restored bus must replay the memoized step result"
    assert _executions["slice"] == 1, "replay after restore must not re-execute"

    print(json.dumps({
        "log_len": len(bus.log),
        "first_deliver": first,
        "second_deliver": second,
        "received": _received,
        "snapshot_keys": sorted(snap.keys()),
    }, indent=2))
