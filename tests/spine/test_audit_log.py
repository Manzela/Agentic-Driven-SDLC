"""Independent verifier test for tools/audit_log.py — hash-chain tamper evidence.

Covers REQ-AUDIT-001..003 / Property 28 / task 52:
  * appending 3 entries chains (each prev_hash == prior entry_hash);
  * verify_chain() True for an untampered chain;
  * mutating a middle entry's reason then re-verifying -> False (tamper detected);
  * the genesis entry's prev_hash is the zero hash.

This test was written independently of the implementer's own tests.
"""
import dataclasses

from tools.audit_log import GENESIS_PREV_HASH, AuditLog, verify_chain


def _append_three(log: AuditLog):
    e1 = log.append("PreToolUse", "Write", "allow", "first", "REQ-AUDIT-001", "implementer.md")
    e2 = log.append("PreToolUse", "Edit", "block", "second", "REQ-AUDIT-002", "implementer.md")
    e3 = log.append("Stop", None, "allow", "third", None, "main")
    return e1, e2, e3


def test_three_entries_chain_links():
    """Each appended entry's prev_hash equals the prior entry's entry_hash."""
    log = AuditLog()
    e1, e2, e3 = _append_three(log)

    # Genesis: first entry chains onto the zero sentinel.
    assert e1.prev_hash == GENESIS_PREV_HASH
    # Each subsequent prev_hash points at the prior entry's entry_hash.
    assert e2.prev_hash == e1.entry_hash
    assert e3.prev_hash == e2.entry_hash
    # seq is 1-based monotonic.
    assert [e.seq for e in (e1, e2, e3)] == [1, 2, 3]


def test_verify_chain_true_untampered():
    """An untampered 3-entry chain verifies True (instance + module verifier)."""
    log = AuditLog()
    _append_three(log)
    assert log.verify_chain() is True
    assert verify_chain(log.entries) is True


def test_tamper_middle_entry_reason_detected():
    """Mutating the middle entry's reason makes verify_chain() return False."""
    log = AuditLog()
    entries = list(_append_three(log))

    # Sanity: clean chain verifies before tampering.
    assert verify_chain(entries) is True

    # AuditEntry is a frozen dataclass; replace the middle entry's reason
    # in place while keeping its stored prev_hash/entry_hash unchanged — the
    # exact "in-place row mutation" Property 28 must catch.
    entries[1] = dataclasses.replace(entries[1], reason="TAMPERED")

    assert verify_chain(entries) is False


def test_genesis_prev_hash_is_zero_hash():
    """The genesis entry's prev_hash is 64 hex zeros."""
    log = AuditLog()
    genesis = log.append("Stop", None, "allow", None, None, "main")
    assert genesis.prev_hash == "0" * 64
    assert genesis.prev_hash == GENESIS_PREV_HASH
    assert len(genesis.prev_hash) == 64
