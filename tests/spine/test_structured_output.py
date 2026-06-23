"""Contract + regression tests for tools/structured_output.py.

These guard the StructuredOutput tool-call boundary against the
"non-final array parameter is silently dropped" serializer defect.

Observed failure mode (the regression these tests pin down): when a
StructuredOutput tool call carried TWO sibling required array properties
(``key_findings: str[]`` and ``recommendations: object[]``), the tool-call
encoder kept only whichever array was emitted LAST and dropped the other
entirely — so schema validation then reported the dropped array "missing".
The drop was position-dependent, not size-dependent: a single-element array
in a non-final position was dropped just the same.

The tests below assert BEHAVIOR (round-trip fidelity + schema validation),
never the wire format, so the codec is free to change as long as every
array parameter survives in any order, at any size.
"""

from __future__ import annotations

import os
import sys

import pytest

# Make the repo's tools/ package importable regardless of pytest's rootdir.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from tools.structured_output import (  # noqa: E402
    StructuredOutputError,
    decode_tool_input,
    encode_tool_input,
    parse_structured_output,
    validate_against_schema,
)

# A schema with TWO sibling required array properties — the exact shape that
# triggered the defect. ``key_findings`` is string[]; ``recommendations`` is
# object[]; ``summary`` is a sibling scalar (must survive too).
TWO_ARRAY_SCHEMA = {
    "type": "object",
    "required": ["summary", "key_findings", "recommendations"],
    "properties": {
        "summary": {"type": "string"},
        "key_findings": {"type": "array", "items": {"type": "string"}},
        "recommendations": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["id", "text"],
                "properties": {
                    "id": {"type": "integer"},
                    "text": {"type": "string"},
                },
            },
        },
    },
}


def _two_array_payload() -> dict:
    """A schema-complete payload with both sibling arrays populated."""
    return {
        "summary": "Audit of the board legibility surface.",
        "key_findings": ["finding A", "finding B", "finding C"],
        "recommendations": [
            {"id": 1, "text": "Tighten card padding to 8px."},
            {"id": 2, "text": "Reserve color for status semantics."},
        ],
    }


def test_two_sibling_arrays_both_survive_round_trip():
    """The core regression: both arrays must survive encode -> decode."""
    payload = _two_array_payload()
    decoded = decode_tool_input(encode_tool_input(payload))
    assert decoded == payload


def test_non_final_array_survives_regardless_of_order():
    """Whichever array is NOT last must not be dropped — test both orderings."""
    findings_last = {
        "recommendations": [{"id": 1, "text": "x"}],
        "key_findings": ["a", "b"],
    }
    recs_last = {
        "key_findings": ["a", "b"],
        "recommendations": [{"id": 1, "text": "x"}],
    }
    assert decode_tool_input(encode_tool_input(findings_last)) == findings_last
    assert decode_tool_input(encode_tool_input(recs_last)) == recs_last


def test_single_element_non_final_array_survives():
    """A single-element array in a non-final slot rules out a size/buffer cause."""
    payload = {"key_findings": ["only one"], "recommendations": [{"id": 1, "text": "x"}]}
    assert decode_tool_input(encode_tool_input(payload)) == payload
    reversed_payload = {"recommendations": [{"id": 1, "text": "x"}], "key_findings": ["only one"]}
    assert decode_tool_input(encode_tool_input(reversed_payload)) == reversed_payload


def test_empty_non_final_array_survives_as_empty_list():
    """An empty array parameter must round-trip as ``[]``, not vanish."""
    payload = {"key_findings": [], "recommendations": [{"id": 1, "text": "x"}]}
    assert decode_tool_input(encode_tool_input(payload)) == payload


def test_three_sibling_arrays_all_survive():
    """The fix must generalize past two arrays."""
    payload = {"a": [1], "b": [2, 3], "note": "scalar in the middle", "c": [4, 5, 6]}
    assert decode_tool_input(encode_tool_input(payload)) == payload


def test_scalars_preserved_alongside_arrays():
    """Scalar siblings interleaved with arrays must survive unchanged."""
    payload = {
        "key_findings": ["a"],
        "count": 3,
        "ok": True,
        "recommendations": [{"id": 1, "text": "x"}],
        "summary": "s",
    }
    assert decode_tool_input(encode_tool_input(payload)) == payload


def test_round_tripped_two_array_object_passes_schema_validation():
    """The whole point: after the boundary, validation must NOT report a missing array."""
    payload = _two_array_payload()
    obj = parse_structured_output(encode_tool_input(payload), TWO_ARRAY_SCHEMA)
    assert obj == payload
    assert set(obj) >= {"key_findings", "recommendations"}


def test_missing_required_array_is_reported_by_validator():
    """The safety net is not a no-op: a genuinely missing array IS flagged."""
    incomplete = {"summary": "s", "key_findings": ["a"]}  # recommendations absent
    errors = validate_against_schema(incomplete, TWO_ARRAY_SCHEMA)
    assert any("recommendations" in e for e in errors)


def test_parse_structured_output_raises_on_missing_required_array():
    """parse_structured_output must raise (not silently pass) on a missing array."""
    incomplete_wire = encode_tool_input({"summary": "s", "key_findings": ["a"]})
    with pytest.raises(StructuredOutputError):
        parse_structured_output(incomplete_wire, TWO_ARRAY_SCHEMA)


def test_validator_reports_type_mismatch_for_non_array():
    """A required-array property carrying a scalar must be a validation error."""
    bad = {"summary": "s", "key_findings": ["a"], "recommendations": "not-an-array"}
    errors = validate_against_schema(bad, TWO_ARRAY_SCHEMA)
    assert errors
