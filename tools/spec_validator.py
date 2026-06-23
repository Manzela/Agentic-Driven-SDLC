"""spec_validator.py — non-LLM EARS spec validator (structural checks).

Per `.kiro/specs/spec-to-evidence-control/design.md`:
`tools/spec_validator.py` is the Non-LLM EARS validator returning
``{contradictions, ambiguities, uncovered, violation_count}`` (Property 14 /
Req 4.1). The full design also describes a Z3-backed EARS->SMT-lib analysis
(Consistency / Completeness / Vacuity / Independence). This module implements
the four-field return contract via the *authoring-time STRUCTURAL checks* —
the non-Z3 checks the design explicitly carves out as not counting toward the
frozen 34-check SMT harness (design.md "two authoring-time structural checks"
plus the four-return-field mapping and the vague-adjective scanner).

Structural rules implemented here (no Z3 / no SMT solve required):

  (a) EARS-pattern uniqueness — every requirement must carry exactly one
      ``ears_pattern`` from the five-pattern enum
      ``{ubiquitous, event-driven, state-driven, unwanted, optional}``;
      zero, multiple, or an out-of-enum value is an AMBIGUITY
      (Req 1.4 / Property 16).

  (b) Vague-adjective scan — any requirement text containing a vague adjective
      from ``{fast, slow, secure, scalable, user-friendly, robust, efficient}``
      is an AMBIGUITY (Property 17 / Req 1.2).

  (c) Completeness — any ``baseline_items`` entry not referenced by any
      requirement's ``covers[]`` is UNCOVERED (Property 14 / Req 4.1).

  (d) Consistency — two requirements sharing the same ``id`` but declaring a
      different ``outcome`` are a CONTRADICTION.

``violation_count = len(contradictions) + len(ambiguities) + len(uncovered)``
(always ``>= 0``), matching the design's four-field mapping.

Pure stdlib. Importable and side-effect free.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

__all__ = [
    "validate_spec",
    "VALID_EARS_PATTERNS",
    "VAGUE_ADJECTIVES",
]

# The five canonical EARS patterns (design.md CoverageItem.ears_pattern enum).
VALID_EARS_PATTERNS = frozenset(
    {"ubiquitous", "event-driven", "state-driven", "unwanted", "optional"}
)

# Vague adjectives flagged as ambiguities (this unit's closed set, per task 10).
VAGUE_ADJECTIVES = frozenset(
    {"fast", "slow", "secure", "scalable", "user-friendly", "robust", "efficient"}
)


def _requirement_text(req: Dict[str, Any]) -> str:
    """Concatenate the human-readable text fields of a requirement.

    The vague-adjective scan looks at whatever prose the requirement carries:
    ``text``, ``ears_statement``/``ears_stmt``, ``statement``, ``description``.
    Missing fields are skipped; non-string values are coerced to ``str``.
    """
    parts: List[str] = []
    for key in ("text", "ears_statement", "ears_stmt", "statement", "description"):
        value = req.get(key)
        if value:
            parts.append(str(value))
    return " ".join(parts)


def _ears_patterns_of(req: Dict[str, Any]) -> List[str]:
    """Return the list of EARS pattern tags declared on a requirement.

    Accepts a single ``ears_pattern`` (str) or a plural ``ears_patterns``
    (list). Both being absent yields an empty list (zero tags -> ambiguity).
    """
    patterns: List[str] = []
    single = req.get("ears_pattern")
    if isinstance(single, str):
        if single.strip():
            patterns.append(single.strip())
    elif single is not None:
        # Non-string, non-None single tag is malformed; count it so the
        # "exactly one valid tag" check still rejects it.
        patterns.append(str(single))

    plural = req.get("ears_patterns")
    if isinstance(plural, (list, tuple)):
        patterns.extend(str(p).strip() for p in plural if str(p).strip())

    return patterns


def _find_vague_adjectives(text: str) -> List[str]:
    """Return the vague adjectives present in ``text`` as whole words.

    Word-boundary matching is case-insensitive. ``user-friendly`` contains a
    hyphen, so we match it against the raw text rather than tokenizing on
    non-word characters.
    """
    if not text:
        return []
    lowered = text.lower()
    hits: List[str] = []
    for adj in VAGUE_ADJECTIVES:
        # \b does not sit cleanly around the hyphen in "user-friendly", so
        # anchor on lookarounds that treat the hyphenated term as one token.
        pattern = r"(?<![\w-])" + re.escape(adj) + r"(?![\w-])"
        if re.search(pattern, lowered):
            hits.append(adj)
    return sorted(hits)


def validate_spec(
    requirements: List[Dict[str, Any]],
    baseline_items: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Validate a spec with non-LLM structural checks.

    Parameters
    ----------
    requirements:
        List of requirement dicts. Recognized keys:
          - ``id`` (str): requirement identifier.
          - ``ears_pattern`` (str) or ``ears_patterns`` (list): EARS tag(s).
          - ``outcome`` (any): the asserted outcome, used for the same-id
            contradiction check.
          - ``covers`` (list[str]): baseline item ids this requirement covers.
          - ``text`` / ``ears_statement`` / ``ears_stmt`` / ``statement`` /
            ``description`` (str): prose scanned for vague adjectives.
    baseline_items:
        Domain-baseline item ids that the spec must cover. ``None`` (the
        default) is treated as an empty baseline -> no uncovered items.

    Returns
    -------
    dict with keys:
        ``contradictions`` (list), ``ambiguities`` (list), ``uncovered``
        (list), ``violation_count`` (int = sum of the three list lengths).
    """
    reqs: List[Dict[str, Any]] = list(requirements or [])
    baseline: List[str] = list(baseline_items or [])

    contradictions: List[Dict[str, Any]] = []
    ambiguities: List[Dict[str, Any]] = []
    uncovered: List[Dict[str, Any]] = []

    # --- (a) EARS-pattern uniqueness + (b) vague-adjective scan -------------
    for index, req in enumerate(reqs):
        if not isinstance(req, dict):
            # A non-dict requirement entry cannot carry exactly one valid EARS
            # tag; treat it as an ambiguity rather than raising.
            ambiguities.append(
                {
                    "index": index,
                    "id": None,
                    "kind": "ears_pattern",
                    "reason": "requirement is not an object",
                    "patterns": [],
                }
            )
            continue

        req_id = req.get("id")

        # (a) exactly-one-valid-EARS-pattern
        patterns = _ears_patterns_of(req)
        valid_patterns = [p for p in patterns if p in VALID_EARS_PATTERNS]
        if len(patterns) != 1 or len(valid_patterns) != 1:
            if len(patterns) == 0:
                reason = "missing ears_pattern"
            elif len(patterns) > 1:
                reason = "multiple ears_pattern tags"
            else:
                reason = "ears_pattern not in valid enum"
            ambiguities.append(
                {
                    "index": index,
                    "id": req_id,
                    "kind": "ears_pattern",
                    "reason": reason,
                    "patterns": patterns,
                }
            )

        # (b) vague-adjective scan
        vague_hits = _find_vague_adjectives(_requirement_text(req))
        if vague_hits:
            ambiguities.append(
                {
                    "index": index,
                    "id": req_id,
                    "kind": "vague_adjective",
                    "reason": "vague adjective(s) without quantification",
                    "adjectives": vague_hits,
                }
            )

    # --- (c) Completeness: baseline items not referenced by any covers[] ----
    covered: set = set()
    for req in reqs:
        if not isinstance(req, dict):
            continue
        covers = req.get("covers")
        if isinstance(covers, (list, tuple, set)):
            covered.update(str(c) for c in covers)

    for item in baseline:
        if str(item) not in covered:
            uncovered.append({"baseline_item": item, "reason": "UNMAPPED"})

    # --- (d) Consistency: same id, different outcome ------------------------
    _SENTINEL = object()
    seen_outcomes: Dict[Any, Any] = {}
    for index, req in enumerate(reqs):
        if not isinstance(req, dict):
            continue
        req_id = req.get("id")
        if req_id is None:
            continue
        outcome = req.get("outcome", _SENTINEL)
        if req_id not in seen_outcomes:
            seen_outcomes[req_id] = outcome
        elif seen_outcomes[req_id] != outcome:
            contradictions.append(
                {
                    "id": req_id,
                    "kind": "outcome_conflict",
                    "reason": "same id with conflicting outcome",
                    "outcomes": [
                        None if seen_outcomes[req_id] is _SENTINEL else seen_outcomes[req_id],
                        None if outcome is _SENTINEL else outcome,
                    ],
                }
            )

    violation_count = len(contradictions) + len(ambiguities) + len(uncovered)

    return {
        "contradictions": contradictions,
        "ambiguities": ambiguities,
        "uncovered": uncovered,
        "violation_count": violation_count,
    }
