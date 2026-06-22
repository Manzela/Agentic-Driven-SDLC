"""INDEPENDENT VERIFIER test for tools/audit_verify.py — hash-chain re-walk.

REQ-AUDIT-002/003 / Property 28 / task 52.2. Written by the independent
verifier, NOT the implementer. It drives the verifier END-TO-END against
chains MINTED by the real producer tools/audit_log.AuditLog and EXPORTED to
plain dict rows (the public ``list[dict]`` input contract of verify_chain),
then asserts the documented Result contract
``{"ok": bool, "broken_at": int | None, "count": int, ...}``:

  * a VALID producer-minted chain verifies ok=True / broken_at=None / count=N;
  * tampering a MIDDLE row in place -> ok=False with broken_at == that index
    (the producer's "0"*64 genesis is auto-selected by the verifier);
  * an EMPTY chain verifies ok=True / count=0.
"""

from __future__ import annotations

import dataclasses
import os
import sys

# Make the repo's tools/ package importable regardless of pytest's rootdir.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from tools.audit_log import AuditLog
from tools.audit_verify import verify_chain


def _export(log: AuditLog) -> list[dict]:
    """Export the producer's AuditEntry rows as plain dicts (public contract)."""
    return [dataclasses.asdict(e) for e in log.entries]


def _build_chain(n: int = 3) -> AuditLog:
    """Mint a valid n-entry chain with the real producer (distinct rows 1..n)."""
    log = AuditLog()
    log.append("PreToolUse", "Write", "allow", "first", "REQ-AUDIT-001", "implementer")
    if n >= 2:
        log.append("PreToolUse", "Edit", "block", "second", "REQ-AUDIT-002", "implementer")
    if n >= 3:
        log.append("Stop", None, "allow", "third", None, "main")
    return log


def test_valid_chain_verifies_ok():
    """A valid producer-minted chain, exported to dicts, verifies ok=True."""
    rows = _export(_build_chain(3))

    result = verify_chain(rows)

    assert result["ok"] is True
    assert result["broken_at"] is None
    assert result["count"] == 3


def test_tampered_middle_entry_breaks_at_that_index():
    """Tampering the MIDDLE row in place -> ok=False, broken_at at that index."""
    rows = _export(_build_chain(3))

    # Sanity: clean chain verifies before tampering.
    assert verify_chain(rows)["ok"] is True

    # In-place mutate the MIDDLE row's reason while keeping its stored
    # entry_hash — exactly the row mutation Property 28 must catch. Middle = 1.
    tampered_index = 1
    rows[tampered_index]["reason"] = "TAMPERED"

    result = verify_chain(rows)

    assert result["ok"] is False
    assert result["broken_at"] == tampered_index
    assert result["count"] == 3


def test_empty_chain_verifies_ok_count_zero():
    """An empty chain verifies ok=True with count=0."""
    result = verify_chain([])

    assert result["ok"] is True
    assert result["broken_at"] is None
    assert result["count"] == 0
