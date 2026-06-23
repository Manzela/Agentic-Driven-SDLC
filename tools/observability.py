"""observability.py — Phase-3 observability primitives (OTel-shaped, pure stdlib).

Spec: .kiro/specs/spec-to-evidence-control/design.md (Phase 3 — observability)
  * Phase-3 row (design.md:16): "OTel + Langfuse + ``requirement.id`` Baggage +
    hook decision forwarding + ``REASONING``-span loop detection (REQ-OBS-006)".
  * Component Inventory ``subagent_stop_hook.py`` row (design.md:130): Phase 3 =
    "the OTel ``hook.decision`` span (task 36.1)".
  * "New / changed components" (design.md:1852): "``REASONING`` span +
    repeated-action loop detector in observability (Phase 3, REQ-OBS-006) …
    implemented as a custom span ATTRIBUTE ``claude.span.kind="reasoning"`` on an
    OTel INTERNAL span — NOT a new ``SpanKind`` enum value (OTel ``SpanKind`` is a
    closed enum {INTERNAL, SERVER, CLIENT, PRODUCER, CONSUMER}). The loop detector
    fires on K=3 identical tool-call signatures."
  * Hook decision forwarding (tasks.md task 36.1, design.md:609-612):
      - Gate-making hooks (Stop, PreToolUse, SubagentStop) emit span name
        ``"hook.decision"`` with ``hook.event``, ``tool.name``, ``decision``
        (allow/block), ``reason``, ``requirement.id`` (+ ``actor_agent`` so the
        live span and the durable ``gate_audit_log`` row carry the same
        attribution). These are the true gate decisions REQ-OBS-003 forwards.
      - Non-gating hooks (PostToolUse / SessionStart / PreCompact) do NOT emit a
        gate-decision allow/block span — only gate-MAKING events get a
        ``hook.decision`` (REQ-OBS-003 is scoped to "WHEN a hook makes a gate
        decision"; design.md:609 calls a uniform decision attr "degenerate for
        the hooks that never gate").

Requirements:
  * REQ-OBS-001 / Req 12.1 — emit OTel spans for model calls, tool invocations,
    subagent tasks (``build_span`` produces the OTel-shaped span dict).
  * REQ-OBS-003 / Req 12.3 — WHEN a hook makes a gate decision, forward
    (event, tool, allow/block, reason, requirement ID) to the trace endpoint
    (``forward_hook_decision`` — gate-making events only).
  * REQ-OBS-004 / Req 12.4 / Property 12 — propagate the active ``requirement.id``
    to spans via W3C Baggage; non-empty value (``build_span`` baggage).
  * REQ-OBS-006 / Requirement 26 — ``REASONING`` span ATTRIBUTE + repeated-action
    reasoning-loop detection at K identical tool-call signatures, DEFAULT K=3
    (``reasoning_loop_signature`` + ``detect_reasoning_loop``).

Properties: Property 12 (W3C Baggage requirement.id propagation); Property 21
  (hook exit-code contract — only gate-making events that MAKE an allow/block
  decision are forwarded as ``hook.decision``); Property 29 referenced by the
  Phase-3 verification suite.

Tasks: 36 / 36.1 (hook decision forwarding), 38 / 38.1 (Phase-3 integration test).

------------------------------------------------------------------------------
OPENTELEMETRY SDK — OPTIONAL, GUARDED
------------------------------------------------------------------------------
The OpenTelemetry SDK is an OPTIONAL dependency. The CORE logic of this module
(span SHAPE, ``requirement.id`` Baggage placement, gate-decision forwarding, and
reasoning-loop detection) is PURE STDLIB and is exercisable without the SDK
installed. When the SDK IS present, :data:`OTEL_AVAILABLE` is True and the
OTel-shaped dicts this module returns map 1:1 onto real SDK span/baggage calls
(see :func:`build_span` field notes). The import is wrapped in try/except so that
importing this module never fails on a host without ``opentelemetry-sdk``.

This keeps the observability primitives deterministically testable (the gate /
loop logic never depends on a live collector) while remaining a faithful shape
for the real OTel export path described in the design.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

__all__ = [
    "OTEL_AVAILABLE",
    "REASONING_LOOP_K",
    "REQUIREMENT_ID_BAGGAGE_KEY",
    "REASONING_SPAN_KIND_ATTR",
    "GATE_MAKING_EVENTS",
    "build_span",
    "build_reasoning_span",
    "forward_hook_decision",
    "reasoning_loop_signature",
    "detect_reasoning_loop",
]

# --------------------------------------------------------------------------- #
# Optional OpenTelemetry SDK import — GUARDED. Core logic is pure stdlib and
# never depends on the SDK being importable.
# --------------------------------------------------------------------------- #
try:  # pragma: no cover - presence depends on the host environment
    from opentelemetry import baggage as _otel_baggage  # type: ignore
    from opentelemetry import trace as _otel_trace  # type: ignore

    OTEL_AVAILABLE = True
except Exception:  # ImportError, or a partially-installed SDK
    _otel_baggage = None  # type: ignore
    _otel_trace = None  # type: ignore
    OTEL_AVAILABLE = False


# --------------------------------------------------------------------------- #
# Constants — pinned to the Requirement-20 threshold registry / design.md.
# --------------------------------------------------------------------------- #

#: REQ-OBS-006 / Requirement 26 reasoning-loop threshold: K identical tool-call
#: signatures recurring consecutively. DEFAULT K = 3 (design.md:375, :475, :1852;
#: "Reasoning-loop K = 3 identical tool-call signatures").
REASONING_LOOP_K: int = 3

#: W3C Baggage key carrying the active requirement id (Req 12.4 / Property 12).
#: The propagated key is ``requirement.id`` (dotted), NOT ``requirement_id``.
REQUIREMENT_ID_BAGGAGE_KEY: str = "requirement.id"

#: REQ-OBS-006: a REASONING span is marked with a custom span ATTRIBUTE on an
#: OTel INTERNAL span — NOT a new SpanKind enum value (OTel SpanKind is the closed
#: enum {INTERNAL, SERVER, CLIENT, PRODUCER, CONSUMER}). (design.md:475, :1852).
REASONING_SPAN_KIND_ATTR: str = "claude.span.kind"
_REASONING_SPAN_KIND_VALUE: str = "reasoning"

#: OTel SpanKind for every span this module produces: INTERNAL. REASONING is an
#: ATTRIBUTE on an INTERNAL span, not a distinct kind.
_INTERNAL_SPAN_KIND: str = "INTERNAL"

#: The hooks that MAKE an allow/block gate decision and whose decision
#: REQ-OBS-003 forwards as a ``hook.decision`` span (design.md:610, :229).
#: PostToolUse / SessionStart / PreCompact are NON-gating and are intentionally
#: absent: they never return allow/block, so emitting a gate-decision span for
#: them would be "degenerate for the hooks that never gate" (design.md:609).
GATE_MAKING_EVENTS = frozenset({"Stop", "PreToolUse", "SubagentStop"})

#: Decision values that constitute an actual gate ALLOW/BLOCK outcome. Anything
#: else (e.g. "n/a", "feedback", None) is NOT a gate decision and is not
#: forwarded as ``hook.decision``.
_GATE_DECISION_VALUES = frozenset({"allow", "block"})


# --------------------------------------------------------------------------- #
# Span construction (REQ-OBS-001 / Req 12.1; REQ-OBS-004 / Req 12.4 / Property 12)
# --------------------------------------------------------------------------- #

def build_span(
    name: str,
    requirement_id: Optional[str] = None,
    attrs: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build an OTel-shaped span dict for a model call / tool / subagent task.

    Faithful to REQ-OBS-001 (Req 12.1 — emit OTel spans) and REQ-OBS-004
    (Req 12.4 / Property 12 — propagate the active ``requirement.id`` via W3C
    Baggage). The returned dict mirrors the shape an OTel ``Span`` carries:

        {
          "name":       <span name>,
          "kind":       "INTERNAL",
          "attributes": { ... user attrs, plus "requirement.id" when given ... },
          "baggage":    { "requirement.id": <id> }  # ONLY when requirement_id set
        }

    ``requirement.id`` is placed in BOTH ``baggage`` (the W3C-Baggage carrier the
    ``RequirementBaggageProcessor`` propagates to child spans — Property 12) AND
    ``attributes`` (so the span is directly queryable by requirement on the
    backend). Per Property 12 the Baggage value must be NON-EMPTY: a ``None`` or
    blank/whitespace ``requirement_id`` adds NO baggage entry (rather than an
    empty one), so "no span associated with requirement-processing is emitted
    WITHOUT this Baggage entry" — a span with no active requirement simply
    carries no requirement baggage, which is the correct, non-violating case.

    Args:
        name: the span name (e.g. ``"model.call"``, ``"tool.Bash"``,
            ``"subagent.verifier"``).
        requirement_id: the active requirement id (e.g. ``"REQ-OBS-006"``), or
            ``None`` when no requirement is active.
        attrs: optional extra span attributes; copied (never mutated in place).

    Returns:
        An OTel-shaped span dict. Pure data — no live span is started here; the
        export path maps this dict onto a real SDK span when OTel is configured.
    """
    attributes: Dict[str, Any] = dict(attrs) if attrs else {}

    span: Dict[str, Any] = {
        "name": name,
        "kind": _INTERNAL_SPAN_KIND,
        "attributes": attributes,
        "baggage": {},
    }

    # Property 12: non-empty requirement.id only. Treat None / "" / whitespace
    # as "no active requirement" — emit no baggage entry rather than an empty one.
    if requirement_id is not None and str(requirement_id).strip() != "":
        rid = str(requirement_id)
        span["baggage"][REQUIREMENT_ID_BAGGAGE_KEY] = rid
        attributes[REQUIREMENT_ID_BAGGAGE_KEY] = rid

    return span


def build_reasoning_span(
    name: str,
    requirement_id: Optional[str] = None,
    attrs: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build a REASONING span (REQ-OBS-006 / Requirement 26).

    A REASONING span is an ordinary INTERNAL span carrying the custom ATTRIBUTE
    ``claude.span.kind="reasoning"`` — NOT a new ``SpanKind`` enum value (OTel
    ``SpanKind`` is the closed enum {INTERNAL, SERVER, CLIENT, PRODUCER,
    CONSUMER}; design.md:475, :1852). The same ``requirement.id`` Baggage rule as
    :func:`build_span` applies.
    """
    span = build_span(name, requirement_id, attrs)
    span["attributes"][REASONING_SPAN_KIND_ATTR] = _REASONING_SPAN_KIND_VALUE
    return span


# --------------------------------------------------------------------------- #
# Hook decision forwarding (REQ-OBS-003 / Req 12.3 / task 36.1)
# --------------------------------------------------------------------------- #

def forward_hook_decision(
    event: str,
    tool: str,
    decision: str,
    reason: str,
    requirement_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Forward a hook gate decision as a ``hook.decision`` span/event.

    REQ-OBS-003 / Req 12.3: "WHEN a hook makes a gate decision, THE System SHALL
    emit that decision — event, tool, allow/block, reason, requirement ID — to
    the same trace endpoint as agent spans." Task 36.1 / design.md:610 pin the
    gate-decision span to name ``"hook.decision"`` with attributes ``hook.event``,
    ``tool.name``, ``decision``, ``reason``, ``requirement.id``.

    CRITICALLY this forwards ONLY for events that ACTUALLY MAKE an allow/block
    decision (design.md:609-612):
      * the event must be a GATE-MAKING hook (Stop / PreToolUse / SubagentStop),
        AND
      * the ``decision`` must be a real gate outcome (``"allow"`` / ``"block"``).
    PostToolUse / SessionStart / PreCompact never gate (exit 1 / exit 0, no
    allow/block); they get a ``hook.feedback`` / informational span elsewhere, NOT
    a ``hook.decision``. For a non-gating event (or a non-allow/block decision)
    this function returns a marker span with ``"forwarded": False`` and does NOT
    populate the gate-decision attribute set — so a degenerate decision attribute
    is never attached to a hook that never gates.

    The ``requirement.id`` is placed in Baggage (Property 12) exactly as in
    :func:`build_span`.

    Args:
        event: the hook event name (e.g. ``"Stop"``, ``"PreToolUse"``,
            ``"SubagentStop"``).
        tool: the tool name the decision concerns (``""`` / ``None`` allowed for
            hooks whose decision is not tool-scoped, e.g. ``Stop``).
        decision: the gate outcome — ``"allow"`` or ``"block"``.
        reason: human-readable reason fed alongside the decision.
        requirement_id: the active requirement id, or ``None``.

    Returns:
        An OTel-shaped span dict. When the event is gate-making AND the decision
        is a real allow/block, the span is named ``"hook.decision"`` and carries
        the full gate-decision attribute set with ``"forwarded": True``. Otherwise
        a ``"hook.non_decision"`` marker span with ``"forwarded": False`` is
        returned and NO gate-decision attribute is set.
    """
    is_gate_making = event in GATE_MAKING_EVENTS
    is_gate_decision = str(decision).strip().lower() in _GATE_DECISION_VALUES

    if not (is_gate_making and is_gate_decision):
        # Not a gate decision REQ-OBS-003 forwards. Return a non-decision marker
        # so callers can distinguish "evaluated, did not forward" from a real
        # gate-decision span — but do NOT attach the allow/block decision attr.
        span = build_span("hook.non_decision", requirement_id)
        span["attributes"]["hook.event"] = event
        span["forwarded"] = False
        return span

    span = build_span("hook.decision", requirement_id)
    span["attributes"].update(
        {
            "hook.event": event,
            "tool.name": tool if tool is not None else "",
            "decision": str(decision).strip().lower(),
            "reason": reason if reason is not None else "",
        }
    )
    span["forwarded"] = True
    return span


# --------------------------------------------------------------------------- #
# Reasoning-loop detection (REQ-OBS-006 / Requirement 26)
# --------------------------------------------------------------------------- #

def reasoning_loop_signature(tool: str, args: Dict[str, Any]) -> str:
    """Compute a STABLE canonical signature for one tool call.

    REQ-OBS-006 flags "identical tool-call signatures recurring ≥ K times". Two
    tool calls that differ only by dict key ORDER, or by insignificant JSON
    whitespace, MUST produce the SAME signature, or genuine repeats would slip
    past the detector. The signature is therefore:

        <tool> + "::" + canonical_json(args)

    where ``canonical_json`` is deterministic: ``sort_keys=True`` (key order
    insensitive), compact separators (no insignificant whitespace),
    ``ensure_ascii=False`` (stable unicode), and ``default=str`` so a
    non-JSON-serializable arg value (e.g. a Path) degrades to a stable string
    rather than raising. ``args`` of ``None`` is normalized to ``{}``.

    The result is a stable string usable directly as a list element for
    :func:`detect_reasoning_loop`.
    """
    canonical_args = json.dumps(
        args if args is not None else {},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    )
    return f"{tool}::{canonical_args}"


def detect_reasoning_loop(
    signatures: List[str],
    k: int = REASONING_LOOP_K,
) -> Dict[str, Any]:
    """Detect a reasoning loop: the SAME signature repeating >= k CONSECUTIVELY.

    REQ-OBS-006 / Requirement 26: flag a repeated-action / reasoning-loop pattern
    when ``>= K`` identical tool-call signatures recur. DEFAULT K = 3 (the
    Requirement-20 threshold registry value, design.md:375/:475/:1852).

    "Recurring" here is CONSECUTIVE repetition — the loop signal is the agent
    doing the SAME thing back-to-back, which is what makes a stuck reasoning loop
    distinct from merely calling the same tool twice across a long, otherwise
    progressing run. A run of length ``>= k`` of one identical signature fires;
    the same signature scattered non-consecutively does not.

    Args:
        signatures: the ordered sequence of per-call signatures (typically built
            by :func:`reasoning_loop_signature`), most-recent last.
        k: the loop threshold (DEFAULT :data:`REASONING_LOOP_K` = 3). A ``k <= 1``
            is clamped to 1 (any single call would otherwise vacuously "loop").

    Returns:
        ``{"loop": bool, "signature": str | None, "count": int}``:
          * ``loop`` — True iff some signature repeats ``>= k`` times consecutively.
          * ``signature`` — the FIRST signature (scanning left-to-right) whose
            consecutive run first reaches length ``k``; ``None`` when no loop.
          * ``count`` — the FULL length of that firing consecutive run (which may
            exceed ``k``); ``0`` when no loop.
    """
    threshold = max(1, int(k))
    n = len(signatures)

    # Single left-to-right pass: find the EARLIEST maximal consecutive run whose
    # length reaches `threshold`, and report that run's FULL length.
    i = 0
    while i < n:
        j = i
        while j < n and signatures[j] == signatures[i]:
            j += 1
        run_len = j - i
        if run_len >= threshold:
            return {"loop": True, "signature": signatures[i], "count": run_len}
        i = j

    return {"loop": False, "signature": None, "count": 0}


if __name__ == "__main__":  # pragma: no cover - manual smoke check
    import sys

    sigs = [reasoning_loop_signature("Bash", {"command": "pytest"}) for _ in range(3)]
    print(json.dumps(detect_reasoning_loop(sigs), indent=2))
    print(json.dumps(forward_hook_decision("Stop", "", "block", "no-progress", "REQ-OBS-006"), indent=2))
    print("OTEL_AVAILABLE=", OTEL_AVAILABLE, file=sys.stderr)
