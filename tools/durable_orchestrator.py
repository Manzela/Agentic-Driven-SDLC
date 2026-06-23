"""durable_orchestrator.py -- Temporal/Inngest-style durable-execution engine.

Spec: .kiro/specs/spec-to-evidence-control/design.md (Phase 5, optional
Temporal/Inngest durable outer loop; "Three independent circuit breakers, any of
which routes to HANDOFF" / design.md:1383-1393) and
.kiro/specs/spec-to-evidence-control/requirements.md Requirement 15 / Orchestration
(REQ-ORCH-001..003), with the HANDOFF terminal-state contract from Requirement 14
(REQ-LOOP-001..003) and Requirement 21 (REQ-LOOP-005 -- HANDOFF ALLOWS termination,
never force-continues / never an infinite block).
Tasks: tasks.md task 43.1 -- "Phase 5 (optional) Temporal/Inngest durable stub
behind a flag -- ``claude -p`` as a durable step, each tool call a separate
activity. _Requirements: 15.2_".

WHAT THIS IS
------------
A *pure-Python reference* of the durable-execution semantics the spec defers to
Temporal/Inngest for. It is deliberately a faithful model of the three properties
that make those engines safe for multi-hour/multi-day crash-safe runs, and NOTHING
that requires a live cluster:

  1. **Activity wrapper** -- :func:`run_activity` runs a side-effecting function
     ("each tool call as a separate activity", REQ-ORCH-002 / 15.2) under a bounded
     :class:`RetryPolicy` (``max_attempts`` + deterministic backoff). On retry
     EXHAUSTION it raises :class:`Handoff` -- the cap/budget terminal state of
     Requirement 14 (REQ-LOOP-001/002/003) -- it NEVER loops forever and NEVER
     silently swallows the failure (the anti-loopmaxxing contract, Requirement 14
     user story: "runaway loops to be impossible").

  2. **Durable workflow + deterministic replay** -- :class:`DurableWorkflow`
     records an APPEND-ONLY :class:`Event` history. Re-running the workflow body
     against an existing history *replays* it: every activity / timer whose result
     is already in history returns that recorded result WITHOUT re-executing the
     side effect, so a crash-restart yields IDENTICAL decisions and re-runs no
     side effects (Temporal's event-sourced replay; the "durable step" of 15.2).

  3. **Checkpoint / resume** -- :func:`DurableWorkflow.checkpoint` serializes the
     history to an opaque, content-addressed blob; :func:`resume` reconstructs an
     equivalent workflow from that blob. This is the durable-state spine of
     Requirement 11 (REQ-STATE-001..004): run state persisted OUTSIDE model context
     so "work resumes exactly where it stopped". The blob carries a SHA-256 over the
     canonical history serialization (the same hash-algorithm / canonical-form
     family used by ``state_integrity.py`` -- ``sort_keys=True`` + compact
     separators + ``hashlib.sha256``) so a corrupted/forged resume is detectable
     (mirrors Requirement 23 resumed-state integrity).

  4. **Durable timer** -- :func:`DurableWorkflow.durable_timer` records a
     ``TIMER_FIRED`` event in history. On replay the timer does NOT sleep again; it
     returns the recorded fire from history. Timers are logical, not wall-clock --
     see DETERMINISM below.

DETERMINISM (the load-bearing invariant)
----------------------------------------
The DECISION PATH reads NO wall-clock and NO ``random``. ``time.time()`` /
``datetime.now()`` / ``random.*`` never appear in the path that produces a
workflow decision; non-determinism that a real engine would feed in (the result
of a side-effecting activity, the moment a timer fires) is captured ONCE into the
event history at first execution and read back verbatim on every replay. Two runs
over the same history therefore make byte-identical decisions. This is the same
"gate outcomes depend only on verifiable facts, no probabilistic prediction"
discipline as Requirement 13.6 / the Z3 determinism checks, applied to the durable
outer loop.

OPTIONAL REAL SDK (guarded / never required)
--------------------------------------------
A real Temporal or Inngest SDK is an OPTIONAL accelerator, never a hard dependency
(Phase 5 is optional, "off by default"). :func:`temporal_sdk_available` /
:func:`inngest_sdk_available` probe for an importable SDK behind a guarded import;
this module's behavior does not change whether or not one is present -- the
pure-Python engine is always the reference. No third-party import is performed at
module load.

PURE STDLIB. Importable and unit-testable with no live Temporal/Inngest cluster,
no Postgres, and no network. Python >= 3.11 (matches pyproject ``requires-python``).
"""

from __future__ import annotations

import dataclasses
import hashlib
import importlib.util
import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

__all__ = [
    # Constants (DEFAULTs mirror requirements.md threshold registry)
    "DEFAULT_MAX_ATTEMPTS",
    "DEFAULT_INITIAL_BACKOFF_SECONDS",
    "DEFAULT_BACKOFF_MULTIPLIER",
    "DEFAULT_MAX_BACKOFF_SECONDS",
    "BLOB_VERSION",
    # Errors / terminal state
    "Handoff",
    "NonDeterminismError",
    # Value types
    "RetryPolicy",
    "EventType",
    "Event",
    # Activity wrapper
    "run_activity",
    "backoff_delays",
    # Durable workflow
    "DurableWorkflow",
    "checkpoint",
    "resume",
    # Optional real-SDK probes (guarded, never required)
    "temporal_sdk_available",
    "inngest_sdk_available",
]

# ---------------------------------------------------------------------------
# DEFAULT constants.
#
# The retry budget DEFAULT mirrors the requirements.md threshold registry:
# "Retry budget = 3 per Slice" (requirements.md:376, REQ-LOOP-003) -- a Slice that
# exhausts 3 retries hands off rather than retrying indefinitely. ``max_attempts``
# is the TOTAL attempt budget (1 initial try + up to 3 retries == 4 attempts);
# expressed as attempts so the wrapper is self-contained.
# ---------------------------------------------------------------------------
DEFAULT_RETRY_BUDGET = 3  # REQ-LOOP-003 retries-after-first DEFAULT
DEFAULT_MAX_ATTEMPTS = DEFAULT_RETRY_BUDGET + 1  # initial attempt + retry budget

# Deterministic exponential backoff DEFAULTs (logical seconds -- the decision path
# never sleeps on them; see RetryPolicy / backoff_delays).
DEFAULT_INITIAL_BACKOFF_SECONDS = 1.0
DEFAULT_BACKOFF_MULTIPLIER = 2.0
DEFAULT_MAX_BACKOFF_SECONDS = 60.0  # hook validator / per-step ceiling family

# Checkpoint-blob schema version. Bumping invalidates older blobs on resume.
BLOB_VERSION = 1


# ===========================================================================
# Terminal state + error types
# ===========================================================================
class Handoff(Exception):  # noqa: N818 - spec-mandated name (REQ-LOOP `raise Handoff`); NOT a generic *Error
    """Terminal HANDOFF state -- raised when a bounded budget is exhausted.

    HANDOFF is "a terminal state distinct from COMPLETE" (requirements.md:38,
    Requirement 14.2 / REQ-LOOP-002): when an activity exhausts its retry budget,
    or a workflow exhausts its activity budget, the engine STOPS and hands off to a
    human -- it does NOT loop forever and does NOT silently mark the work complete.

    Per Requirement 21 (REQ-LOOP-005, the infinite-block fix), HANDOFF is an ALLOW
    termination: the run is permitted to stop so a human can pick it up; it is NOT a
    force-continuation. In this engine that maps to *raising* (the durable step ends
    and surfaces the handoff) rather than re-entering the retry loop.

    Attributes
    ----------
    reason:
        One of ``"cap-reached"`` / ``"budget-exceeded"`` / ``"no-progress"`` /
        ``"retry-budget-exhausted"`` -- the circuit-breaker that fired
        (design.md:1383-1387, mirrors the ``emit_handoff_summary`` reasons).
    activity:
        The activity / step name whose budget was exhausted (if applicable).
    attempts:
        How many attempts were made before handing off.
    last_error:
        The final underlying exception (chained as ``__cause__``), retained so a
        human can audit WHY the run handed off (Requirement 14.4 -- bound
        comprehension debt with human-readable evidence).
    """

    def __init__(
        self,
        reason: str,
        *,
        activity: str | None = None,
        attempts: int | None = None,
        last_error: BaseException | None = None,
    ) -> None:
        self.reason = reason
        self.activity = activity
        self.attempts = attempts
        self.last_error = last_error
        detail = f"HANDOFF[{reason}]"
        if activity is not None:
            detail += f" activity={activity!r}"
        if attempts is not None:
            detail += f" attempts={attempts}"
        if last_error is not None:
            detail += f" last_error={type(last_error).__name__}: {last_error}"
        super().__init__(detail)


class NonDeterminismError(Exception):
    """Raised when a replay diverges from recorded history.

    Replay safety (Temporal's "non-determinism error"): if the workflow body, on
    replay, requests a DIFFERENT activity/timer than the one recorded at that
    history position, the recorded history can no longer be trusted to reproduce
    the original decisions. Rather than silently re-execute a side effect or make a
    contradictory decision, the engine refuses -- the durable-outer-loop analogue
    of the resumed-state-integrity block (Requirement 23 / CHECK-11a/11b).
    """


# ===========================================================================
# Retry policy
# ===========================================================================
@dataclass(frozen=True)
class RetryPolicy:
    """Bounded retry policy for :func:`run_activity` (REQ-LOOP-001/003).

    ``max_attempts`` is the TOTAL attempt budget (initial attempt included), so
    ``max_attempts=4`` == 1 try + 3 retries (the DEFAULT retry budget). It MUST be
    >= 1; a non-positive budget would mean "never run", which is a config error.

    Backoff is deterministic exponential with a ceiling: delay before attempt *k*
    (1-indexed, for k >= 2) is
    ``min(initial * multiplier**(k-2), max_backoff)``. The delays are LOGICAL
    seconds recorded in history for audit/observability; the decision path does NOT
    sleep on them and never reads the wall clock, so replay is deterministic. A
    real Temporal worker would honor the same schedule against real time.

    ``non_retryable`` lists exception type *names* (e.g. ``"ValueError"``) that
    must FAIL FAST -- a non-retryable error hands off immediately without consuming
    the remaining attempt budget. :class:`Handoff` itself is ALWAYS non-retryable
    (a downstream handoff must propagate, never be retried into a loop).
    """

    max_attempts: int = DEFAULT_MAX_ATTEMPTS
    initial_backoff_seconds: float = DEFAULT_INITIAL_BACKOFF_SECONDS
    backoff_multiplier: float = DEFAULT_BACKOFF_MULTIPLIER
    max_backoff_seconds: float = DEFAULT_MAX_BACKOFF_SECONDS
    non_retryable: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be >= 1 (the initial attempt counts)")
        if self.initial_backoff_seconds < 0:
            raise ValueError("initial_backoff_seconds must be >= 0")
        if self.backoff_multiplier < 1.0:
            raise ValueError("backoff_multiplier must be >= 1.0")
        if self.max_backoff_seconds < 0:
            raise ValueError("max_backoff_seconds must be >= 0")

    def delay_before_attempt(self, attempt: int) -> float:
        """Logical backoff delay (seconds) before 1-indexed ``attempt``.

        Attempt 1 (the initial try) has no preceding delay (returns ``0.0``).
        Deterministic: a pure function of the policy and the attempt number, with
        no wall-clock and no randomness.
        """
        if attempt <= 1:
            return 0.0
        raw = self.initial_backoff_seconds * (self.backoff_multiplier ** (attempt - 2))
        return float(min(raw, self.max_backoff_seconds))

    def is_non_retryable(self, exc: BaseException) -> bool:
        """True if ``exc`` must fail fast (no further retries)."""
        if isinstance(exc, Handoff):
            return True
        return type(exc).__name__ in self.non_retryable


def backoff_delays(policy: RetryPolicy) -> list[float]:
    """Return the full deterministic backoff schedule for ``policy``.

    The list has ``max_attempts`` entries: index *i* is the delay before attempt
    ``i+1`` (so index 0 is ``0.0``). Exposed for tests/observability so the
    schedule can be asserted without invoking any activity.
    """
    return [policy.delay_before_attempt(i + 1) for i in range(policy.max_attempts)]


# ===========================================================================
# Activity wrapper
# ===========================================================================
def run_activity(
    fn: Callable[..., Any],
    *args: Any,
    retry_policy: RetryPolicy | None = None,
    activity_name: str | None = None,
    **kwargs: Any,
) -> Any:
    """Run ``fn(*args, **kwargs)`` as a durable ACTIVITY under bounded retries.

    Each tool call is a separate activity (REQ-ORCH-002 / requirements.md 15.2).
    The function is attempted up to ``retry_policy.max_attempts`` times. On a
    retryable failure the next attempt is taken (a real worker would wait
    ``policy.delay_before_attempt(k)`` first; the schedule is deterministic and
    wall-clock-free so this reference does not sleep). On budget EXHAUSTION the
    wrapper raises :class:`Handoff` -- the anti-loopmaxxing terminal state
    (Requirement 14, REQ-LOOP-003) -- it NEVER retries indefinitely and NEVER
    silently returns a failure as success.

    A non-retryable error (per ``policy.non_retryable``, or any :class:`Handoff`
    raised by ``fn``) hands off immediately without consuming the rest of the
    budget.

    Parameters
    ----------
    fn:
        The side-effecting callable (the "tool call"). MUST be re-runnable: the
        retry contract is at-least-once, so ``fn`` should be idempotent or
        tolerate re-execution, exactly as a Temporal activity must.
    retry_policy:
        Bounded :class:`RetryPolicy`. Defaults to the DEFAULT budget (1 + 3).
    activity_name:
        Label carried into the :class:`Handoff` for auditability; defaults to
        ``fn.__name__``.

    Returns
    -------
    The return value of the first SUCCESSFUL ``fn`` call.

    Raises
    ------
    Handoff:
        When the retry budget is exhausted, or ``fn`` raised a non-retryable error.
        ``Handoff.last_error`` (and ``__cause__``) carry the final underlying
        exception for human audit.
    """
    policy = retry_policy if retry_policy is not None else RetryPolicy()
    name = activity_name or getattr(fn, "__name__", "anonymous_activity")

    last_error: BaseException | None = None
    attempts_made = 0
    for attempt in range(1, policy.max_attempts + 1):
        attempts_made = attempt
        try:
            return fn(*args, **kwargs)
        except Handoff:
            # A downstream HANDOFF must propagate verbatim, never be retried.
            raise
        except BaseException as exc:  # noqa: BLE001 -- bounded retry needs the broad catch
            last_error = exc
            if policy.is_non_retryable(exc):
                raise Handoff(
                    "retry-budget-exhausted",
                    activity=name,
                    attempts=attempt,
                    last_error=exc,
                ) from exc
            # else: fall through to the next attempt (if budget remains).

    # Budget exhausted across all attempts -> HANDOFF (REQ-LOOP-003). Never loop.
    raise Handoff(
        "retry-budget-exhausted",
        activity=name,
        attempts=attempts_made,
        last_error=last_error,
    ) from last_error


# ===========================================================================
# Event history (append-only, event-sourced)
# ===========================================================================
class EventType:
    """The append-only history event-type vocabulary (string enum)."""

    WORKFLOW_STARTED = "WORKFLOW_STARTED"
    ACTIVITY_COMPLETED = "ACTIVITY_COMPLETED"
    ACTIVITY_FAILED = "ACTIVITY_FAILED"
    TIMER_FIRED = "TIMER_FIRED"
    WORKFLOW_COMPLETED = "WORKFLOW_COMPLETED"
    WORKFLOW_HANDOFF = "WORKFLOW_HANDOFF"


@dataclass(frozen=True)
class Event:
    """A single append-only history event.

    ``seq`` is the monotonically increasing 0-indexed position (the event-sourcing
    sequence number). ``name`` scopes the command (activity/timer name) so replay
    can assert the body requested the SAME command at this position. ``payload`` is
    the recorded result -- for an activity, its return value; for a timer, the
    fire marker. Payloads MUST be JSON-serializable so the history is durable and
    canonically hashable.
    """

    seq: int
    type: str
    name: str
    payload: Any = None

    def to_dict(self) -> dict[str, Any]:
        return {"seq": self.seq, "type": self.type, "name": self.name, "payload": self.payload}

    @staticmethod
    def from_dict(d: dict[str, Any]) -> Event:
        return Event(
            seq=int(d["seq"]),
            type=str(d["type"]),
            name=str(d["name"]),
            payload=d.get("payload"),
        )


def _canonical_json(obj: Any) -> str:
    """Canonical, deterministic JSON serialization (matches state_integrity.py).

    ``sort_keys=True`` + compact separators so insertion order and whitespace never
    affect the bytes -- the same canonical form the resumed-state hash is taken
    over (state_integrity.canonical_state_repr).
    """
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _history_hash(events: Sequence[Event]) -> str:
    """SHA-256 over the canonical serialization of the event history.

    Same hash-algorithm / canonical-form family as ``state_integrity`` so a
    corrupted or forged checkpoint blob is detectable on resume (Requirement 23
    resumed-state integrity).
    """
    canonical = _canonical_json([e.to_dict() for e in events])
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ===========================================================================
# Durable workflow
# ===========================================================================
class DurableWorkflow:
    """Event-sourced durable workflow with deterministic replay.

    A workflow BODY is an ordinary Python callable ``body(wf, *args)`` that issues
    commands through ``wf`` -- :meth:`run_activity` for side effects and
    :meth:`durable_timer` for delays. The engine records each command's result in
    an APPEND-ONLY :class:`Event` history.

    Replay: re-running :meth:`execute` against an existing history does NOT
    re-execute side effects whose result is already recorded. At each command the
    engine first looks for the recorded event at the current replay cursor; if
    present, it returns that recorded payload and advances the cursor (the side
    effect is SKIPPED). Only commands BEYOND the recorded history actually execute.
    A crash-restart therefore reproduces every prior decision identically and runs
    no recorded side effect twice -- Temporal's event-sourced durability, and the
    durable-step contract of requirements.md 15.2.

    Determinism: the body MUST be deterministic given its recorded inputs -- no
    wall-clock, no ``random``, no unrecorded I/O in the decision path. All
    non-determinism enters ONLY through recorded activity results and timer fires.
    """

    def __init__(self, workflow_id: str, history: list[Event] | None = None) -> None:
        self.workflow_id = workflow_id
        self.history: list[Event] = list(history) if history is not None else []
        # Replay cursor: index into ``history`` of the next recorded event to
        # consume. While the cursor is < len(history) we are REPLAYING (return
        # recorded results, skip side effects); once it reaches the end we are
        # executing live (run side effects, append new events).
        self._cursor = 0
        # Per-(type,name) counter to disambiguate repeated commands of the same
        # name within a single run, so replay matching is position-stable.
        self._command_index: dict[tuple[str, str], int] = {}

    # -- internal helpers ---------------------------------------------------
    @property
    def is_replaying(self) -> bool:
        """True while the replay cursor is still inside recorded history."""
        return self._cursor < len(self.history)

    def _next_command_ordinal(self, event_type: str, name: str) -> int:
        key = (event_type, name)
        ordinal = self._command_index.get(key, 0)
        self._command_index[key] = ordinal + 1
        return ordinal

    def _record(self, event_type: str, name: str, payload: Any) -> Event:
        event = Event(seq=len(self.history), type=event_type, name=name, payload=payload)
        self.history.append(event)
        return event

    def _replay_or_execute(
        self,
        event_type: str,
        name: str,
        produce: Callable[[], Any],
    ) -> Any:
        """Core event-sourcing primitive shared by activities and timers.

        If a recorded event sits at the replay cursor, validate it matches the
        requested ``(event_type, name)`` and return its recorded payload WITHOUT
        calling ``produce`` (no side effect on replay). Otherwise call ``produce``
        to generate the result live and APPEND it to history.
        """
        # Track command ordinal for diagnostics / stable positioning.
        self._next_command_ordinal(event_type, name)

        if self._cursor < len(self.history):
            recorded = self.history[self._cursor]
            if recorded.type != event_type or recorded.name != name:
                raise NonDeterminismError(
                    f"replay divergence at seq={recorded.seq}: history has "
                    f"{recorded.type}:{recorded.name!r} but body requested "
                    f"{event_type}:{name!r}"
                )
            self._cursor += 1
            return recorded.payload

        # Beyond recorded history: execute live and append.
        payload = produce()
        self._record(event_type, name, payload)
        self._cursor = len(self.history)  # stay at the live frontier
        return payload

    # -- workflow commands --------------------------------------------------
    def run_activity(
        self,
        fn: Callable[..., Any],
        *args: Any,
        retry_policy: RetryPolicy | None = None,
        activity_name: str | None = None,
        **kwargs: Any,
    ) -> Any:
        """Durable activity command.

        On the live frontier this runs ``fn`` under the bounded retry policy via
        the module-level :func:`run_activity` and records its result as an
        ``ACTIVITY_COMPLETED`` event. On replay it returns the recorded result and
        ``fn`` is NEVER called again (no duplicate side effect).

        A :class:`Handoff` from the bounded retry wrapper is recorded as a
        ``WORKFLOW_HANDOFF`` event (so the handoff is itself durable / replayable)
        and then re-raised -- the durable step ends in the HANDOFF terminal state
        (REQ-LOOP-003 / REQ-LOOP-005), never an infinite retry.

        The activity result MUST be JSON-serializable (it is persisted in history).
        """
        name = activity_name or getattr(fn, "__name__", "anonymous_activity")

        def _produce() -> Any:
            try:
                return run_activity(
                    fn, *args, retry_policy=retry_policy, activity_name=name, **kwargs
                )
            except Handoff as h:
                # Durably record the handoff before surfacing it, so a replay sees
                # the same terminal outcome and does not re-attempt the activity.
                self._record(
                    EventType.WORKFLOW_HANDOFF,
                    name,
                    {"reason": h.reason, "attempts": h.attempts},
                )
                self._cursor = len(self.history)
                raise

        return self._replay_or_execute(EventType.ACTIVITY_COMPLETED, name, _produce)

    def durable_timer(self, name: str, seconds: float) -> dict[str, Any]:
        """Durable timer command -- records a ``TIMER_FIRED`` event in history.

        The timer is LOGICAL: it records that a timer named ``name`` for
        ``seconds`` fired. The decision path does NOT sleep and does NOT read the
        wall clock, so replay is deterministic -- on replay the recorded fire is
        returned without waiting. A real Temporal/Inngest worker would durably
        sleep ``seconds`` of real time before recording the same fire.

        Returns the recorded fire marker ``{"timer": name, "seconds": float,
        "fired": True}``.
        """
        if seconds < 0:
            raise ValueError("durable_timer seconds must be >= 0")
        marker = {"timer": name, "seconds": float(seconds), "fired": True}
        return self._replay_or_execute(EventType.TIMER_FIRED, name, lambda: marker)

    # -- driver -------------------------------------------------------------
    def execute(self, body: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Run (or replay) ``body(self, *args, **kwargs)`` to completion.

        On a FRESH workflow this records ``WORKFLOW_STARTED`` then runs the body,
        appending events for each command. On a RESUMED workflow (history
        pre-loaded) it replays recorded commands first (skipping their side
        effects) and only executes commands beyond the recorded frontier.

        On normal return, a ``WORKFLOW_COMPLETED`` event is recorded (idempotently
        -- not duplicated on replay) and the body's return value is returned. A
        :class:`Handoff` propagating out of the body surfaces as the HANDOFF
        terminal state (the engine does not catch/retry it).
        """
        if not self.history:
            self._record(EventType.WORKFLOW_STARTED, self.workflow_id, {"args": _safe(args)})
            self._cursor = len(self.history)
        else:
            # Resumed: replay from the top. Skip the leading WORKFLOW_STARTED if
            # present so the cursor lands on the first command event.
            self._cursor = 0
            if self.history and self.history[0].type == EventType.WORKFLOW_STARTED:
                self._cursor = 1
            self._command_index.clear()

        result = body(self, *args, **kwargs)

        if not any(e.type == EventType.WORKFLOW_COMPLETED for e in self.history):
            self._record(EventType.WORKFLOW_COMPLETED, self.workflow_id, {"result": _safe(result)})
        return result

    # -- checkpoint / resume ------------------------------------------------
    def checkpoint(self) -> str:
        """Serialize this workflow's durable state to an opaque blob (a string).

        The blob is canonical JSON carrying the schema version, the workflow id,
        the full append-only history, and a SHA-256 integrity hash over the
        canonical history serialization. It contains NO live Python objects -- only
        the recorded, JSON-serializable history -- so it can be persisted to the
        durable store / file and survive a process crash (Requirement 11,
        REQ-STATE-001).
        """
        events = [e.to_dict() for e in self.history]
        blob_obj = {
            "version": BLOB_VERSION,
            "workflow_id": self.workflow_id,
            "history": events,
            "history_hash": _history_hash(self.history),
        }
        return _canonical_json(blob_obj)

    @staticmethod
    def resume(blob: str) -> DurableWorkflow:
        """Reconstruct a workflow from a :meth:`checkpoint` blob.

        Validates the schema version and verifies the recorded ``history_hash``
        against a freshly recomputed hash of the history. A hash mismatch raises
        :class:`NonDeterminismError` rather than resuming onto corrupted/forged
        state -- the durable-outer-loop analogue of the resumed-state-integrity
        block (Requirement 23 / CHECK-11a/11b): a false or corrupted resume is
        refused, never silently trusted.

        The returned workflow has its cursor at the top, ready for :meth:`execute`
        to replay the recorded history deterministically.
        """
        try:
            obj = json.loads(blob)
        except (ValueError, TypeError) as exc:
            raise NonDeterminismError(f"checkpoint blob is not valid JSON: {exc}") from exc
        if not isinstance(obj, dict):
            raise NonDeterminismError("checkpoint blob must be a JSON object")
        if obj.get("version") != BLOB_VERSION:
            raise NonDeterminismError(
                f"checkpoint blob version {obj.get('version')!r} != supported {BLOB_VERSION}"
            )
        raw_events = obj.get("history")
        if not isinstance(raw_events, list):
            raise NonDeterminismError("checkpoint blob 'history' must be a list")
        events = [Event.from_dict(e) for e in raw_events]

        recomputed = _history_hash(events)
        recorded = obj.get("history_hash")
        if recorded != recomputed:
            raise NonDeterminismError(
                "checkpoint history hash mismatch -- corrupted or forged resume "
                f"(recorded={recorded!r}, recomputed={recomputed!r})"
            )

        workflow_id = str(obj.get("workflow_id", ""))
        return DurableWorkflow(workflow_id=workflow_id, history=events)


def _safe(obj: Any) -> Any:
    """Best-effort JSON-safe projection of an arbitrary value for history.

    Recorded payloads MUST be JSON-serializable. Body args / results that are not
    natively serializable are projected to ``repr`` so a checkpoint never fails to
    serialize; the decision-relevant payloads (activity results, timer fires) are
    expected to already be JSON-native.
    """
    try:
        json.dumps(obj)
        return obj
    except (TypeError, ValueError):
        if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
            return _safe(dataclasses.asdict(obj))
        if isinstance(obj, list | tuple):
            return [_safe(x) for x in obj]
        if isinstance(obj, dict):
            return {str(k): _safe(v) for k, v in obj.items()}
        return repr(obj)


# Module-level convenience aliases mirroring the requested checkpoint(state)->blob
# and resume(blob)->state surface (here "state" IS the DurableWorkflow, whose
# durable state is its event history).
def checkpoint(workflow: DurableWorkflow) -> str:
    """Serialize ``workflow``'s durable state to a blob (see
    :meth:`DurableWorkflow.checkpoint`)."""
    return workflow.checkpoint()


def resume(blob: str) -> DurableWorkflow:
    """Reconstruct a workflow from a blob (see :meth:`DurableWorkflow.resume`)."""
    return DurableWorkflow.resume(blob)


# ===========================================================================
# Optional real-SDK probes (guarded, never required)
# ===========================================================================
def _module_importable(module_name: str) -> bool:
    """True if ``module_name`` is importable WITHOUT importing it.

    Uses ``importlib.util.find_spec`` so no third-party package is actually loaded
    at probe time -- Phase 5 real-SDK support is optional and must never become a
    hard import dependency of this reference engine.
    """
    try:
        return importlib.util.find_spec(module_name) is not None
    except (ImportError, ValueError, ModuleNotFoundError):
        return False


def temporal_sdk_available() -> bool:
    """True if the real Temporal Python SDK (``temporalio``) is installed.

    Probe only -- the pure-Python engine above is always the reference and its
    behavior does not depend on this. A production deployment may bind activities
    to a real Temporal worker when this returns True (REQ-ORCH-002 / 15.2).
    """
    return _module_importable("temporalio")


def inngest_sdk_available() -> bool:
    """True if the real Inngest Python SDK (``inngest``) is installed.

    Probe only -- see :func:`temporal_sdk_available`.
    """
    return _module_importable("inngest")


if __name__ == "__main__":  # pragma: no cover - manual smoke
    # Tiny deterministic smoke: an activity that fails twice then succeeds, a
    # durable timer, replay equivalence, and checkpoint/resume round-trip.
    calls: dict[str, int] = {"flaky": 0}

    def flaky() -> str:
        calls["flaky"] += 1
        if calls["flaky"] < 3:
            raise RuntimeError("transient")
        return "ok"

    def body(wf: DurableWorkflow) -> dict[str, Any]:
        a = wf.run_activity(flaky)
        t = wf.durable_timer("settle", 5)
        return {"activity": a, "timer": t}

    wf1 = DurableWorkflow("smoke-1")
    out1 = wf1.execute(body)
    print(f"run 1 result      : {out1}")
    print(f"flaky invocations : {calls['flaky']} (1 initial + 2 retries == 3)")
    print(f"history length    : {len(wf1.history)}")

    blob = checkpoint(wf1)
    print(f"checkpoint blob   : {len(blob)} bytes")

    # Resume + replay: side effects must NOT re-run, decision must be identical.
    pre = calls["flaky"]
    wf2 = resume(blob)
    out2 = wf2.execute(body)
    print(f"run 2 (replay)    : {out2}")
    print(f"flaky re-invoked  : {calls['flaky'] - pre} (must be 0 on replay)")
    print(f"deterministic     : {out1 == out2}")

    # HANDOFF on exhaustion.
    def always_fail() -> None:
        raise RuntimeError("permanent")

    try:
        run_activity(always_fail, retry_policy=RetryPolicy(max_attempts=2))
    except Handoff as h:
        print(f"handoff on exhaust: reason={h.reason!r} attempts={h.attempts}")

    print(f"temporal sdk      : {temporal_sdk_available()}")
    print(f"inngest sdk       : {inngest_sdk_available()}")
