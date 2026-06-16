"""Independent verifier for S2-evidence (REQ-COV-003/006 / task 3.1).

These tests do NOT trust tools/evidence_collector.py — they exercise its
public contract directly and assert the documented behavior:

  * collect() yields a record that validate_evidence_record accepts.
  * collected_at is timezone-aware (parsed datetime .tzinfo is not None).
  * a record missing a required field is rejected.
  * an empty-string field is rejected.
  * output_hash="sha256:xyz" (present-but-malformed) is rejected.
  * collected_at="not-a-date" is rejected.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime

# Make the repo's tools/ package importable regardless of pytest's rootdir.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from tools.evidence_collector import collect, validate_evidence_record


def _good_record():
    """A freshly collected, contract-complete record."""
    return collect(
        test_file="tests/spine/test_evidence_collector.py",
        test_name="test_collect_yields_valid_record",
        output="raw artifact output bytes -> hashed",
    )


def test_collect_yields_record_accepted_by_validator():
    record = _good_record()
    assert isinstance(record, dict)
    # All four contract fields present.
    assert set(record) >= {"test_file", "test_name", "output_hash", "collected_at"}
    # The validator must accept what the collector produces.
    assert validate_evidence_record(record) is True


def test_collected_at_is_timezone_aware():
    record = _good_record()
    parsed = datetime.fromisoformat(record["collected_at"])
    # A naive datetime.utcnow().isoformat() would have tzinfo is None and would
    # be coerced on a TIMESTAMPTZ insert — the implementer must use an aware dt.
    assert parsed.tzinfo is not None
    assert parsed.utcoffset() is not None


def test_missing_field_is_rejected():
    record = _good_record()
    del record["test_name"]
    assert validate_evidence_record(record) is False


def test_empty_string_field_is_rejected():
    record = _good_record()
    record["test_file"] = ""
    assert validate_evidence_record(record) is False
    # Whitespace-only must also be rejected (non-empty after strip).
    record2 = _good_record()
    record2["test_name"] = "   "
    assert validate_evidence_record(record2) is False


def test_bad_output_hash_is_rejected():
    record = _good_record()
    # Present but malformed: right prefix, wrong (too short, non-hex) body.
    record["output_hash"] = "sha256:xyz"
    assert validate_evidence_record(record) is False


def test_bad_collected_at_is_rejected():
    record = _good_record()
    record["collected_at"] = "not-a-date"
    assert validate_evidence_record(record) is False
