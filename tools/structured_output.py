"""structured_output.py — the StructuredOutput tool-call boundary codec + safety net.

Spec context: ``docs/reference-architecture/Agentic-Driven SDLC.md`` makes
"structured-output schema enforcement" a first-class verification concern —
"For Claude specifically, structured output is via tool-use + JSON schema;
always validate with Pydantic/Zod as a safety net." This module is that safety
net for the Python side of the loop: the deterministic glue that an
orchestrator uses to (a) serialize the parameters an agent passes to the
``StructuredOutput`` tool, (b) reconstruct them on the orchestrator side, and
(c) validate the reconstructed object against the call's JSON Schema before any
downstream code trusts it.

Why a per-parameter codec instead of one ``json.dumps`` blob: a tool call is
assembled parameter by parameter (mirroring how the tool-use API streams the
input as ``input_json_delta`` fragments and how an orchestrator reconstructs
named parameters one at a time). The encoder therefore emits one record per
parameter rather than one monolithic object.

THE DEFECT THIS MODULE PINS DOWN
--------------------------------
A StructuredOutput call carrying TWO sibling required array properties
(``key_findings: str[]`` and ``recommendations: object[]``) deterministically
lost whichever array was NOT emitted last: the surviving array was always the
final one, and schema validation then reported the dropped array "missing".
It was position-dependent, not size-dependent — a single-element array in a
non-final slot was dropped the same way. Root cause: the encoder reordered
array parameters to the end of the call (so a partial-JSON consumer completes
the scalars first) but held "the array parameter" in a SINGLE slot, so each
array overwrote the previous one and only the last reached the wire.

The fix keeps the reorder-arrays-last intent but accumulates EVERY array
parameter, so all arrays survive in any order, at any size. See
``tests/spine/test_structured_output.py`` for the regression.

Pure stdlib + ``jsonschema`` (already a dev dependency). Side-effect free.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any

from jsonschema import Draft202012Validator

__all__ = [
    "StructuredOutputError",
    "decode_tool_input",
    "encode_tool_input",
    "parse_structured_output",
    "validate_against_schema",
]


class StructuredOutputError(ValueError):
    """Raised when a decoded StructuredOutput object fails schema validation.

    Carries the structured ``errors`` (a list of human-readable messages) and
    the offending decoded ``obj`` so callers can log or surface both.
    """

    def __init__(self, errors: Sequence[str], obj: Any = None) -> None:
        self.errors: list[str] = list(errors)
        self.obj = obj
        super().__init__("; ".join(self.errors) or "structured output failed validation")


def _is_array(value: Any) -> bool:
    """A JSON ``array`` parameter is a ``list`` (str/bytes are scalars)."""
    return isinstance(value, list)


def encode_tool_input(params: Mapping[str, Any]) -> str:
    """Serialize the parameters of a StructuredOutput tool call to the wire form.

    The wire form is JSON-lines: one ``{"name", "kind", "value"}`` record per
    parameter. Array parameters are emitted AFTER the scalar parameters so that
    a streaming / partial-JSON consumer completes the scalar fields first.
    """
    scalar_records: list[dict[str, Any]] = []
    array_records: list[dict[str, Any]] = []  # accumulate EVERY array param, not just one
    for name, value in params.items():
        if _is_array(value):
            # Every array parameter is kept; emitting them after the scalars
            # preserves the reorder-arrays-last intent without losing any.
            array_records.append({"name": name, "kind": "array", "value": value})
        else:
            scalar_records.append({"name": name, "kind": "scalar", "value": value})

    ordered = scalar_records + array_records
    return "\n".join(json.dumps(record, ensure_ascii=False) for record in ordered)


def decode_tool_input(wire: str) -> dict[str, Any]:
    """Reconstruct the parameter mapping from the wire form produced by ``encode_tool_input``."""
    out: dict[str, Any] = {}
    for line in wire.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        record = json.loads(stripped)
        out[record["name"]] = record["value"]
    return out


def validate_against_schema(obj: Any, schema: Mapping[str, Any]) -> list[str]:
    """Return a list of human-readable validation problems (empty list == valid).

    This is the "safety net": it delegates to a JSON Schema (Draft 2020-12)
    validator and surfaces EVERY problem (e.g. a required array reported as a
    missing property), sorted by location for stable output.
    """
    validator = Draft202012Validator(dict(schema))
    errors = sorted(validator.iter_errors(obj), key=lambda e: (list(e.path), e.message))
    return [_format_error(e) for e in errors]


def _format_error(error: Any) -> str:
    """Render a jsonschema error as ``<path>: <message>`` (path-less errors keep just the message)."""
    location = "/".join(str(p) for p in error.path)
    return f"{location}: {error.message}" if location else error.message


def parse_structured_output(wire: str, schema: Mapping[str, Any]) -> dict[str, Any]:
    """Decode a StructuredOutput tool call and validate it against ``schema``.

    Returns the decoded object on success. Raises :class:`StructuredOutputError`
    (carrying the list of problems) if validation fails — so a dropped or
    malformed required array can never be silently accepted downstream.
    """
    obj = decode_tool_input(wire)
    errors = validate_against_schema(obj, schema)
    if errors:
        raise StructuredOutputError(errors, obj)
    return obj
