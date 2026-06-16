"""req_id_scan.py — single source of truth for requirement-ID extraction.

Per `.kiro/specs/spec-to-evidence-control/tasks.md` (task 20.1 / task 29.1,
Reconciliation 2026-06-16 "shared trailer helper"): the
``[A-Z]+-[A-Z]+-[0-9]{3}`` commit-trailer / comment ID-extraction regex is
factored into ONE shared helper imported by BOTH ``orphan_detector.py``
(task 20.1, REQ-6.3 / Property 11 — bidirectional orphan detection) AND
``traceability_writer.py`` (task 29.1, REQ-6.2 / Property 10 —
commit-has-req-id gate), to prevent regex drift / double-maintenance.

The pattern matches the canonical 3-segment ``CoverageItem.id`` form
``REQ-<DOMAIN>-NNN`` (e.g. ``REQ-TRACE-001``, ``REQ-VERIFY-007``,
``REQ-SPEC-018``) — explicitly NOT the dotted EARS criterion numbers
(e.g. ``6.3``), which are a different namespace this regex cannot match.

PURE STDLIB (``re`` only).
"""

from __future__ import annotations

import re
from typing import List

__all__ = ["REQ_ID_PATTERN", "REQ_ID_RE", "scan_req_ids"]

# Canonical requirement-ID pattern. Unanchored at the module level so it can be
# searched *within* comments, docstrings, and commit-message bodies; callers
# that need a whole-string match (e.g. a schema check) should anchor with
# ``re.fullmatch`` instead. ``\b`` word boundaries keep ``REQ-SPEC-001`` from
# matching inside a longer alphanumeric run while still matching mid-line.
REQ_ID_PATTERN = r"\b[A-Z]+-[A-Z]+-[0-9]{3}\b"
REQ_ID_RE = re.compile(REQ_ID_PATTERN)


def scan_req_ids(text: str) -> List[str]:
    """Return every requirement ID found in ``text``, in first-seen order.

    De-duplicates while preserving order so a commit body or source comment
    that mentions the same ID twice yields it once. Returns an empty list for
    ``None``/empty/non-matching input (never raises on benign input).
    """
    if not text:
        return []
    seen: dict[str, None] = {}
    for match in REQ_ID_RE.findall(text):
        seen.setdefault(match, None)
    return list(seen.keys())
