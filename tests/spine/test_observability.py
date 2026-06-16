"""Independent verifier suite for tools/observability.py (Phase-3 observability).

Covers REQ-OBS-001..006 / Property 21,29 / tasks 36,38:
  * build_span includes requirement.id when provided, omits it when None;
  * forward_hook_decision yields decision + reason + requirement_id fields;
  * reasoning_loop_signature is stable for equal (tool,args), differs otherwise;
  * detect_reasoning_loop fires loop=True at 3 identical consecutive signatures
    (count>=3) and loop=False for varied input or runs of <3.

These assertions are written from the spec the verifier was handed, NOT copied
from the implementer's own tests.
"""

from tools.observability import (
    REQUIREMENT_ID_BAGGAGE_KEY,
    build_span,
    detect_reasoning_loop,
    forward_hook_decision,
    reasoning_loop_signature,
)

# --------------------------------------------------------------------------- #
# build_span: requirement.id present iff a non-empty requirement is given.
# --------------------------------------------------------------------------- #


def test_build_span_includes_requirement_id_when_provided():
    span = build_span("model.call", requirement_id="REQ-OBS-006")
    # Propagated via W3C Baggage (Property 12) AND queryable as an attribute.
    assert span["baggage"].get(REQUIREMENT_ID_BAGGAGE_KEY) == "REQ-OBS-006"
    assert span["attributes"].get(REQUIREMENT_ID_BAGGAGE_KEY) == "REQ-OBS-006"
    assert span["name"] == "model.call"


def test_build_span_omits_requirement_id_when_none():
    span = build_span("tool.Bash", requirement_id=None)
    # No active requirement -> no baggage entry at all (not an empty one).
    assert REQUIREMENT_ID_BAGGAGE_KEY not in span["baggage"]
    assert REQUIREMENT_ID_BAGGAGE_KEY not in span["attributes"]
    assert span["baggage"] == {}


def test_build_span_omits_requirement_id_when_blank():
    # Whitespace/blank is treated as "no active requirement" (non-empty rule).
    for blank in ("", "   ", "\t"):
        span = build_span("tool.X", requirement_id=blank)
        assert REQUIREMENT_ID_BAGGAGE_KEY not in span["baggage"]
        assert REQUIREMENT_ID_BAGGAGE_KEY not in span["attributes"]


# --------------------------------------------------------------------------- #
# forward_hook_decision: gate-making event yields decision + reason + req id.
# --------------------------------------------------------------------------- #


def test_forward_hook_decision_yields_decision_reason_requirement_fields():
    span = forward_hook_decision(
        event="PreToolUse",
        tool="Bash",
        decision="block",
        reason="no-authority",
        requirement_id="REQ-OBS-003",
    )
    attrs = span["attributes"]
    assert attrs["decision"] == "block"
    assert attrs["reason"] == "no-authority"
    # requirement id rides in Baggage per Property 12, and is queryable as attr.
    assert span["baggage"].get(REQUIREMENT_ID_BAGGAGE_KEY) == "REQ-OBS-003"
    assert attrs.get(REQUIREMENT_ID_BAGGAGE_KEY) == "REQ-OBS-003"
    assert attrs["hook.event"] == "PreToolUse"
    assert attrs["tool.name"] == "Bash"


def test_forward_hook_decision_allow_is_forwarded():
    span = forward_hook_decision("Stop", "", "allow", "progress-made", "REQ-OBS-001")
    assert span["attributes"]["decision"] == "allow"
    assert span["attributes"]["reason"] == "progress-made"


def test_forward_hook_decision_non_gating_event_not_forwarded():
    # PostToolUse never makes an allow/block gate decision (Property 21).
    span = forward_hook_decision("PostToolUse", "Bash", "allow", "r", "REQ-OBS-003")
    assert span.get("forwarded") is False
    # And no degenerate decision attribute is attached.
    assert "decision" not in span["attributes"]


# --------------------------------------------------------------------------- #
# reasoning_loop_signature: stable for equal (tool, args), differs otherwise.
# --------------------------------------------------------------------------- #


def test_signature_stable_for_equal_tool_and_args():
    a = reasoning_loop_signature("Bash", {"command": "pytest -q"})
    b = reasoning_loop_signature("Bash", {"command": "pytest -q"})
    assert a == b


def test_signature_stable_under_key_reordering():
    a = reasoning_loop_signature("Edit", {"path": "x.py", "line": 3})
    b = reasoning_loop_signature("Edit", {"line": 3, "path": "x.py"})
    assert a == b


def test_signature_differs_for_different_args():
    a = reasoning_loop_signature("Bash", {"command": "pytest -q"})
    b = reasoning_loop_signature("Bash", {"command": "pytest -x"})
    assert a != b


def test_signature_differs_for_different_tool():
    a = reasoning_loop_signature("Bash", {"command": "ls"})
    b = reasoning_loop_signature("Grep", {"command": "ls"})
    assert a != b


# --------------------------------------------------------------------------- #
# detect_reasoning_loop: fires at 3 identical consecutive signatures (count>=3),
# does not fire for varied input or runs shorter than 3.
# --------------------------------------------------------------------------- #


def test_detect_loop_fires_at_three_identical_consecutive():
    sig = reasoning_loop_signature("Bash", {"command": "pytest"})
    result = detect_reasoning_loop([sig, sig, sig])
    assert result["loop"] is True
    assert result["signature"] == sig
    assert result["count"] >= 3


def test_detect_loop_count_reports_full_run_length():
    sig = reasoning_loop_signature("Bash", {"command": "pytest"})
    result = detect_reasoning_loop([sig, sig, sig, sig])
    assert result["loop"] is True
    assert result["count"] == 4


def test_detect_no_loop_for_two_identical():
    sig = reasoning_loop_signature("Bash", {"command": "pytest"})
    result = detect_reasoning_loop([sig, sig])
    assert result["loop"] is False
    assert result["count"] == 0
    assert result["signature"] is None


def test_detect_no_loop_for_varied_signatures():
    a = reasoning_loop_signature("Bash", {"command": "a"})
    b = reasoning_loop_signature("Bash", {"command": "b"})
    c = reasoning_loop_signature("Bash", {"command": "c"})
    # Three calls, all different -> no consecutive run of 3.
    result = detect_reasoning_loop([a, b, c])
    assert result["loop"] is False


def test_detect_no_loop_for_non_consecutive_repeats():
    a = reasoning_loop_signature("Bash", {"command": "a"})
    b = reasoning_loop_signature("Bash", {"command": "b"})
    # 'a' appears 3 times but never 3-in-a-row.
    result = detect_reasoning_loop([a, b, a, b, a])
    assert result["loop"] is False


def test_detect_empty_sequence_no_loop():
    result = detect_reasoning_loop([])
    assert result["loop"] is False
    assert result["count"] == 0
