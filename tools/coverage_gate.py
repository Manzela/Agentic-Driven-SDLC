#!/usr/bin/env python3
"""coverage_gate.py — OPA-equivalent zero-evidence merge gate (Python).

Spec: .kiro/specs/spec-to-evidence-control/tasks.md, task 21 (21.1)
Requirements: 5.7, 10.3 — REQ-GATE-002 mirror at the merge boundary.
Property: Property 22 (OPA Zero-Evidence Policy at Merge), design.md ~line 1613.

This module is the Python twin of ``.github/policies/coverage_query.rego``.
The two are kept LOGICALLY IDENTICAL: ``deny_merge`` produces exactly the deny
set the Rego ``deny`` rules produce when Conftest evaluates ``feature_list.json``
as its document input. The Python form exists so the gate is unit-testable
without an OPA/Conftest runtime; the Rego form is what CI actually runs.

The merge gate mirrors the Stop completion gate (``stop_hook.evaluate_stop``):

  * It counts ONLY in-scope items — ``input.items`` filtered to ``in_scope ==
    true`` (Req 5.7), matching ``evaluate_stop``'s ``in_scope_items``. An
    out-of-scope item NEVER contributes a deny reason.
  * Any in-scope item whose ``status`` is not EXACTLY ``"proven"`` denies the
    merge — a ``failed`` in-scope item blocks identically to ``unproven``,
    matching the Stop hook's
    ``not_proven = [i for i in in_scope_items if i.status != "proven"]``.
  * Any in-scope item that IS ``proven`` but lacks a complete four-field
    Evidence_Record (``test_file``, ``test_name``, ``output_hash``,
    ``collected_at`` — each present AND non-empty) denies the merge. This keeps
    the merge gate aligned with the in-session SubagentStop four-field gate /
    Property 2; a proven item carrying a partial evidence object that the
    in-session gate would reject must not slip through at merge.
  * An EMPTY coverage model — zero items, or zero in-scope items — denies the
    merge. A zero-item model is a valid INIT state but never a valid
    COMPLETE/merge state and must not vacuously satisfy the gate. This mirrors
    ``evaluate_stop``'s empty-coverage-model block.

``deny_merge`` is a PURE function over a plain dict (the parsed
``feature_list.json``) and returns ``{"deny": bool, "reasons": [str, ...]}``.
It fails CLOSED: any error, or a non-dict / missing ``items`` document, yields
``deny=True`` rather than a vacuous pass — an ambiguous merge gate must resolve
to blocked, not passed (REQ-GATE-005).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

__all__ = [
    "EVIDENCE_FIELDS",
    "deny_merge",
]

# The four required Evidence_Record fields. Mirrors
# evidence_collector.EvidenceRecord / the JSON-Schema EvidenceRecord.required
# list and the Rego ``evidence_fields`` set. ``actor_agent`` / ``evidence_kind``
# are provenance, NOT part of the four-field proven-transition gate.
EVIDENCE_FIELDS = ("test_file", "test_name", "output_hash", "collected_at")


def _norm_session(value: Any) -> str:
    """Normalize a session id for distinctness comparison.

    Session ids are UNTRUSTED inputs in Phase A. Two ids that differ only by
    surrounding whitespace or letter-case are the SAME actor for the purpose of
    the actor-separation gate — an implementer must not be able to dodge the
    self-grading check by submitting ``' i '`` as the verifier when it
    implemented as ``'i'``. We strip surrounding whitespace, REJECT non-ASCII
    (→ ``""``), then case-fold. A non-string, ``None``, empty/whitespace-only, or
    non-ASCII id normalizes to ``""`` (treated as absent). ASCII-only is enforced
    so this is IDENTICAL to the Rego ``_norm_session`` twin (OPA ``lower`` over
    ASCII == Python ``casefold`` over ASCII); a non-ASCII id such as ``'ß'``
    (which ``casefold`` folds to ``'ss'`` but Rego ``lower`` does not) collapses
    to ``""`` in BOTH, closing the casefold/lower drift. Phase B additionally
    rejects any id absent from the trusted ledger.
    """
    if not isinstance(value, str):
        return ""
    s = value.strip()
    if not s or not s.isascii():
        return ""
    return s.casefold()  # == lower() for ASCII; matches the Rego twin


def _is_nonempty_str_field(evidence: Dict[str, Any], field: str) -> bool:
    """True iff ``evidence[field]`` is a present, NON-EMPTY STRING.

    The schema declares every Evidence_Record field ``type: string, minLength: 1``,
    so a NON-string value (null / bool / number / list) is invalid evidence — NOT a
    present field. The earlier code coerced non-strings (``str(value)``) and so
    accepted ``test_file: false`` as complete, while the Rego twin denied it: a
    rego⇔python split exactly where this gate must be identical (red-team). Both
    twins now require a non-empty string and agree across null/false/[]/number.
    """
    value = evidence.get(field)
    return isinstance(value, str) and value.strip() != ""


def _evidence_complete(item: Dict[str, Any]) -> bool:
    """Return True iff ``item`` carries a complete four-field Evidence_Record: an
    ``evidence`` mapping present AND every ``EVIDENCE_FIELDS`` field a non-empty
    string. Mirrors the Rego ``field_missing_or_empty`` helper (negated)."""
    evidence = item.get("evidence")
    if not isinstance(evidence, dict):
        return False
    return all(_is_nonempty_str_field(evidence, field) for field in EVIDENCE_FIELDS)


def _evidence_obj(item: Dict[str, Any]) -> Dict[str, Any]:
    """The item's ``evidence`` mapping, or ``{}`` when absent/non-dict (Rule 3-4 input)."""
    ev = item.get("evidence")
    return ev if isinstance(ev, dict) else {}


def _model_shape_denial(feature_list: Any) -> Optional[Dict[str, Any]]:
    """Fail-CLOSED deny dict for a malformed model SHAPE (not-an-object / no ``items`` /
    ``items`` not an array), or ``None`` when the shape is valid. Reasons are
    verbatim-identical to the original inline checks (rego-twin / parity-oracle stable)."""
    if not isinstance(feature_list, dict):
        return {"deny": True, "reasons": [
            "Merge denied: feature_list is not an object "
            f"(got {type(feature_list).__name__}). Fail closed."]}
    items = feature_list.get("items")
    if items is None:
        return {"deny": True, "reasons": [
            "Merge denied: feature_list.json has no 'items' array. "
            "Fail closed."]}
    if not isinstance(items, list):
        return {"deny": True, "reasons": [
            "Merge denied: feature_list.json 'items' is not an array "
            f"(got {type(items).__name__}). Fail closed."]}
    return None


def _deny_reason_status(item_id: Any, status: Any) -> Optional[str]:
    """Rule 1 — status gate. Anything not EXACTLY 'proven' denies (a 'failed' in-scope
    item blocks identically to 'unproven'). Returns the reason, or None for a proven item.
    A non-proven item cannot also be missing-evidence, so the caller short-circuits on it."""
    if status != "proven":
        return (f"Merge denied: in-scope item {item_id!r} has "
                f"status={status!r} (not 'proven').")
    return None


def _deny_reason_evidence(item_id: Any, item: Dict[str, Any]) -> Optional[str]:
    """Rule 2 — evidence gate. A proven in-scope item MUST carry a complete four-field
    Evidence_Record; returns the missing/empty-field reason, or None when complete."""
    if _evidence_complete(item):
        return None
    ev_obj = _evidence_obj(item)
    missing = [f for f in EVIDENCE_FIELDS if not _is_nonempty_str_field(ev_obj, f)]
    return (f"Merge denied: in-scope item {item_id!r} is 'proven' but "
            f"its Evidence_Record is missing/empty field(s): {missing}.")


def _deny_reasons_actor_sep(item_id: Any, ev: Dict[str, Any]) -> List[str]:
    """Rule 3 — actor-separation. A proven item's evidence must name DISTINCT
    implementer/verifier sessions (zero-trust: an implementer may not self-verify).
    Both ids are NORMALIZED (strip + case-fold) first so a whitespace/case near-duplicate
    cannot masquerade as distinct, and emptiness is checked on the normalized form.
    Mirrors the Rego ``_norm_session`` / ``_distinct_sessions`` twin. Phase A trusts the
    ids; Phase B adds cryptographic attestation + ledger cross-check at CI."""
    vs_norm = _norm_session(ev.get("verifier_session_id"))
    is_norm = _norm_session(ev.get("implementer_session_id"))
    if not vs_norm or not is_norm:
        return [f"Merge denied: in-scope item {item_id!r} is 'proven' but its "
                f"evidence lacks verifier_session_id / implementer_session_id."]
    if vs_norm == is_norm:
        return [f"Merge denied: in-scope item {item_id!r} evidence has the same "
                f"verifier and implementer session (self-grading)."]
    return []


def _deny_reason_wiring_kind(item_id: Any, item: Dict[str, Any], ev: Dict[str, Any]) -> Optional[str]:
    """Rule 4 — WIRING integration-evidence gate. A proven WIRING item MUST be proven with
    INTEGRATION-test evidence (evidence_kind == 'integration'); a unit/behavioral/perf/a11y
    record cannot prove a wiring obligation (Req 8.3 / Property 2). Rego twin:
    coverage_query.rego Rule 5; the schema allOf is the write-time gate. Non-WIRING items
    are unaffected. Returns the reason, or None."""
    if item.get("type") != "WIRING":
        return None
    kind = ev.get("evidence_kind")
    if kind != "integration":
        return (f"Merge denied: in-scope WIRING item {item_id!r} is 'proven' but its "
                f"Evidence_Record.evidence_kind is {kind!r} (must be 'integration').")
    return None


def deny_merge(feature_list: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate the zero-evidence merge gate over a ``feature_list.json`` dict.

    Returns ``{"deny": bool, "reasons": [str, ...]}``. ``deny`` is True iff at
    least one reason was produced. Reasons are deterministic and ordered by item
    id so the output is stable across runs (mirroring Conftest's deterministic
    deny set). Fails CLOSED on any error or malformed input.

    The per-item rule cascade is extracted into ``_deny_reason_*`` helpers; this
    body is the orchestrator. The append ORDER (status → evidence → actor-sep →
    wiring, per item, items sorted by id) and the ``continue`` after a non-proven
    status are load-bearing — they fix the deterministic deny set the Rego twin
    (coverage_query.rego) and the parity oracle (test_opa_conftest.py) assert.
    """
    reasons: List[str] = []
    try:
        shape_denial = _model_shape_denial(feature_list)
        if shape_denial is not None:
            return shape_denial

        # Filter to in-scope items BEFORE any status/evidence check (Req 5.7). STRICT
        # boolean `is True` — NOT truthy — to stay logically identical to the Rego twin's
        # `item.in_scope == true` (a truthy check let a non-bool in_scope through while Rego
        # excluded it — whole-branch review I5; schema requires in_scope:boolean anyway).
        in_scope_items = [
            i for i in feature_list.get("items") if isinstance(i, dict) and i.get("in_scope") is True
        ]

        # Empty-coverage-model gate. Zero in-scope items is a valid INIT state but never a
        # valid COMPLETE/merge state — deny so it cannot vacuously satisfy the gate (Property 22).
        if not in_scope_items:
            return {"deny": True, "reasons": [
                "Merge denied: feature_list.json has zero in-scope items. "
                "A zero-item coverage model is a valid INIT state but never "
                "a valid COMPLETE/merge state."]}

        # Stable ordering by id so the deny set is deterministic.
        ordered = sorted(in_scope_items, key=lambda i: str(i.get("id", "")))

        for item in ordered:
            item_id = item.get("id", "<no-id>")
            status_reason = _deny_reason_status(item_id, item.get("status"))
            if status_reason is not None:
                reasons.append(status_reason)
                continue  # a non-proven item cannot also be missing-evidence.
            ev = _evidence_obj(item)
            evidence_reason = _deny_reason_evidence(item_id, item)
            if evidence_reason is not None:
                reasons.append(evidence_reason)
            reasons.extend(_deny_reasons_actor_sep(item_id, ev))
            wiring_reason = _deny_reason_wiring_kind(item_id, item, ev)
            if wiring_reason is not None:
                reasons.append(wiring_reason)

        return {"deny": bool(reasons), "reasons": reasons}

    except Exception as exc:  # noqa: BLE001 — fail CLOSED on any error.
        return {"deny": True, "reasons": [
            f"Merge denied: coverage_gate raised "
            f"{type(exc).__name__}: {exc}. Fail closed."]}


# ── CLI shell ───────────────────────────────────────────────────────────────
# Thin I/O wrapper for ad-hoc use / parity with the Conftest invocation
# (``conftest test feature_list.json``). Reads a feature_list.json path argv[1]
# (or stdin), evaluates, prints the decision, and exits 0 on allow / 1 on deny.
# All decision logic lives in deny_merge; this shell is intentionally trivial.

def main(argv: List[str] | None = None) -> int:
    import json
    import sys

    argv = sys.argv[1:] if argv is None else argv
    try:
        if argv:
            with open(argv[0], "r", encoding="utf-8") as fh:
                doc = json.load(fh)
        else:
            raw = sys.stdin.read()
            doc = json.loads(raw) if raw.strip() else {}
    except (OSError, json.JSONDecodeError) as exc:
        result = {
            "deny": True,
            "reasons": [f"Merge denied: could not load feature_list: {exc}."],
        }
        print(json.dumps(result, indent=2))
        return 1

    result = deny_merge(doc)
    print(json.dumps(result, indent=2))
    return 1 if result["deny"] else 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
