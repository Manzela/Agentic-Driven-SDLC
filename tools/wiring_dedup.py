"""wiring_dedup.py — UNION-OF-CONCERNS de-dup of WIRING dead-code candidates (Task 10).

Spec §2.1 / Property T6: a qualname is a FINDING if EITHER source flags it.
  - AST verdict:     ``wiring.reachable == False``  → ORPHAN (finding)
  - Semgrep verdict: ``status`` is a non-empty, non-"clean" string → finding
  - Semgrep "clean" NEVER retracts an AST orphan (union, not intersection).
  - A qualname that is NOT flagged by either source is OMITTED.

The merged output is a list of schema-valid WIRING CoverageItem candidates that feed
Task 8's ``ingest_wiring_candidates`` directly. Two consequences for the merge shape
(red-team):
  * the Semgrep verdict is surfaced under ``semgrep_status`` — NOT ``status`` — so it
    never clobbers the CoverageItem lifecycle ``status`` (which the schema constrains to
    unproven/proven/failed; a Semgrep "dead" would reject the whole ingest batch);
  * a Semgrep-only finding (no AST counterpart) is SYNTHESIZED into a full unproven
    WIRING item (id/type/wiring/...) so it survives ingest's qualname de-dup rather than
    being silently dropped.

``merge`` is a pure function: inputs are deep-copied, never mutated.
"""

from __future__ import annotations

import copy
import hashlib
from typing import Any

__all__ = ["merge"]


def _ast_is_orphan(item: dict[str, Any]) -> bool:
    """True when the AST candidate marks the symbol unreachable (wiring.reachable False)."""
    wiring = item.get("wiring")
    return isinstance(wiring, dict) and wiring.get("reachable") is False


def _semgrep_is_finding(item: dict[str, Any]) -> bool:
    """True when the Semgrep candidate flags the symbol dead. Only an explicit
    non-empty, non-"clean" STRING status is a finding — an absent / empty / non-string
    status defaults to clean, so it never manufactures a spurious finding (red-team
    F2/F3: case-insensitive, empty-string-safe)."""
    status = item.get("status")
    return isinstance(status, str) and status.strip().casefold() not in ("", "clean")


def _enrich_with_semgrep(merged: dict[str, Any], sg: dict[str, Any]) -> None:
    """Copy Semgrep metadata onto the merged item. The Semgrep verdict lands under
    ``semgrep_status`` (NOT ``status``) so the CoverageItem lifecycle status is preserved."""
    if "status" in sg:
        merged["semgrep_status"] = sg["status"]
    for key in ("decorator", "callback", "reason"):
        if key in sg:
            merged[key] = sg[key]


def _synthesize_item(sg: dict[str, Any]) -> dict[str, Any]:
    """Build a schema-valid unproven WIRING CoverageItem from a Semgrep-only finding so
    it is ingestible (red-team F4). The id is derived deterministically from the qualname
    (id pattern ^[A-Z]+-[A-Z]+-[0-9]{3}$); file/line are best-effort from the Semgrep row."""
    qn = str(sg.get("qualname"))
    digits = int(hashlib.sha256(qn.encode("utf-8")).hexdigest(), 16) % 1000
    item: dict[str, Any] = {
        "id": f"REQ-WIRE-{digits:03d}",
        "type": "WIRING",
        "priority": 999,
        "dependencies": [],
        "acceptance_criteria": [f"Symbol {qn!r} must be reachable from a real execution path."],
        "status": "unproven",
        "in_scope": True,
        "qualname": qn,
        "wiring": {
            "symbol": qn, "qualname": qn,
            "file": sg.get("file", "<semgrep>"), "line": sg.get("line", 0),
            "reachable": False, "source": "semgrep_custom_rule",
        },
        "reachable": False,
    }
    _enrich_with_semgrep(item, sg)
    return item


def merge(
    ast_candidates: list[dict[str, Any]],
    semgrep_candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return the union-of-concerns WIRING findings, one schema-ingestible dict per
    qualname, sorted by qualname (deterministic).

    A qualname is a finding iff the AST marks it unreachable OR Semgrep flags it dead;
    a Semgrep "clean" never retracts an AST orphan; a qualname flagged by neither is
    omitted. For a qualname with an AST item the merged dict is the (deep-copied) AST
    item with ``reachable`` surfaced top-level (the AST verdict) and Semgrep metadata
    enriched under ``semgrep_status``/``decorator``/...; a Semgrep-only finding is
    synthesized into a full unproven WIRING item.
    """
    ast_by_qn: dict[str, dict[str, Any]] = {
        item["qualname"]: item for item in ast_candidates if item.get("qualname") is not None
    }
    sg_by_qn: dict[str, dict[str, Any]] = {
        item["qualname"]: item for item in semgrep_candidates if item.get("qualname") is not None
    }

    findings: list[dict[str, Any]] = []
    for qualname in sorted(set(ast_by_qn) | set(sg_by_qn), key=str):
        ast_item = ast_by_qn.get(qualname)
        sg_item = sg_by_qn.get(qualname)

        ast_orphan = ast_item is not None and _ast_is_orphan(ast_item)
        sg_finding = sg_item is not None and _semgrep_is_finding(sg_item)
        if not ast_orphan and not sg_finding:
            continue  # flagged by neither source — omit.

        if ast_item is not None:
            merged = copy.deepcopy(ast_item)  # deep copy: never mutate the caller's input.
            wiring = ast_item.get("wiring")
            if isinstance(wiring, dict):
                # Top-level `reachable` reflects the AST verdict (may be True on a
                # Semgrep-driven finding — the union verdict is "is in this list").
                merged["reachable"] = wiring.get("reachable")
            if sg_item is not None:
                _enrich_with_semgrep(merged, sg_item)
        else:
            merged = _synthesize_item(sg_item)  # Semgrep-only → synthesize an ingestible item.

        findings.append(merged)

    return findings
