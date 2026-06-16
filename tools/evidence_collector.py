"""evidence_collector.py — Evidence_Record builder and validator.

Spec: .kiro/specs/spec-to-evidence-control/tasks.md, task 3.1
Requirements: 5.3, 5.6, 8.3, 9.3, 25.1, 25.2

An Evidence_Record is the four-field proof object that the coverage control
plane requires before any in-scope item may transition into ``proven``:

    {
        "test_file":    <str>,   # the test/artifact source path
        "test_name":    <str>,   # the specific test / artifact identifier
        "output_hash":  "sha256:<64 lowercase hex>",  # sha256 of the artifact
        "collected_at": <RFC-3339 / ISO-8601 timezone-aware timestamp>,
    }

This module is PURE STDLIB. It is imported by the SubagentStop hook
(.claude/hooks/subagent_stop_hook.py) and the PreToolUse status guard, which
both delegate four-field + format validation to ``validate_evidence_record``.
Keeping the validator and the collector in one module guarantees the in-session
gate and the record builder enforce exactly the same contract.
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Dict

__all__ = [
    "EvidenceRecord",
    "OUTPUT_HASH_PATTERN",
    "collect",
    "validate_evidence_record",
]

# Type alias for readability at call sites. An EvidenceRecord is a plain dict so
# it round-trips through JSON / Postgres / the hook stdin boundary without any
# custom (de)serialization.
EvidenceRecord = Dict[str, str]

# Anchored four-field hash format. ``output_hash`` MUST be the literal prefix
# ``sha256:`` followed by exactly 64 lowercase hex characters — the form emitted
# by ``"sha256:" + hashlib.sha256(...).hexdigest()``. Anchored (^...$) so that a
# present-but-malformed hash (uppercase hex, missing prefix, wrong length,
# trailing junk) is rejected rather than silently accepted (task 3.1 / 3.3).
OUTPUT_HASH_PATTERN = re.compile(r"^sha256:[a-f0-9]{64}$")

# The four required fields, in canonical order. Single-sourced so the collector,
# the validator, and any caller enumerate the exact same set.
_REQUIRED_FIELDS = ("test_file", "test_name", "output_hash", "collected_at")


def collect(test_file: str, test_name: str, output: str) -> EvidenceRecord:
    """Build a complete four-field Evidence_Record from a verification artifact.

    Parameters
    ----------
    test_file:
        Path / identifier of the test file or artifact source that produced the
        evidence.
    test_name:
        The specific test name or artifact identifier within ``test_file``.
    output:
        The raw artifact output as text. For WIRING items this is the
        integration-test result exercising the real execution path
        (REQ-EXEC-012 / 8.3); for NFR items it is the k6 / Lighthouse / axe-core
        result artifact (REQ-VERIFY-007/008 / 25.1/25.2); for functional items
        it is the behavioral / unit / Playwright test output.

    Returns
    -------
    EvidenceRecord
        A dict with all four required keys:

        * ``test_file``    — echoed input.
        * ``test_name``    — echoed input.
        * ``output_hash``  — ``"sha256:"`` + the SHA-256 hex digest of
          ``output`` (UTF-8 encoded), lowercase hex, matching
          ``OUTPUT_HASH_PATTERN``.
        * ``collected_at`` — ``datetime.now(timezone.utc).isoformat()``, a
          TIMEZONE-AWARE RFC-3339 string carrying a ``+00:00`` offset. (NOT
          naive ``datetime.utcnow()`` — the EvidenceRecord schema requires
          ``format: date-time`` and ``evidence_records.collected_at`` is
          ``TIMESTAMPTZ``; a naive string has no offset and would be coerced to
          a different instant on Postgres insert, breaking Property 19's
          loss-free round-trip.)
    """
    output_hash = "sha256:" + hashlib.sha256(output.encode("utf-8")).hexdigest()
    collected_at = datetime.now(timezone.utc).isoformat()
    return {
        "test_file": test_file,
        "test_name": test_name,
        "output_hash": output_hash,
        "collected_at": collected_at,
    }


def validate_evidence_record(record: dict) -> bool:
    """Return ``True`` iff ``record`` is a complete, well-formed Evidence_Record.

    The record is valid only when ALL of the following hold:

    1. ``record`` is a ``dict``.
    2. All four required fields are present AND non-empty.
    3. ``output_hash`` matches the anchored pattern ``^sha256:[a-f0-9]{64}$``
       (lowercase hex, ``sha256:`` prefix present, exactly 64 hex chars).
    4. ``collected_at`` parses as an ISO-8601 timestamp via
       ``datetime.fromisoformat``.

    Returns ``False`` on any violation. This is the same validator the
    SubagentStop hook and the PreToolUse status guard call, so a present-but-
    malformed ``output_hash`` (uppercase hex / missing prefix / wrong length) or
    an unparseable ``collected_at`` is rejected here — not just absent fields.
    """
    if not isinstance(record, dict):
        return False

    # (2) Presence + non-empty for every required field. A field counts as empty
    # if it is missing, ``None``, or — after stripping — an empty string.
    for field in _REQUIRED_FIELDS:
        value = record.get(field)
        if value is None:
            return False
        if not isinstance(value, str):
            return False
        if value.strip() == "":
            return False

    # (3) output_hash format.
    if OUTPUT_HASH_PATTERN.match(record["output_hash"]) is None:
        return False

    # (4) collected_at must parse as ISO-8601. ``fromisoformat`` raises
    # ValueError on a malformed string; a TypeError guards against any non-str
    # slipping past the presence check above.
    try:
        datetime.fromisoformat(record["collected_at"])
    except (ValueError, TypeError):
        return False

    return True
