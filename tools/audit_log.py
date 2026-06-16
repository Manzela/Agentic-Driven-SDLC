"""audit_log.py — tamper-evident gate-decision audit-log PRODUCER (hash chain).

Spec: .kiro/specs/spec-to-evidence-control/design.md
  * Component Inventory row `audit_log.py` (Phase 2): audit-log PRODUCER —
    ``append(event, tool, decision, reason, requirement_id, actor_agent)``,
    called by ``stop_hook.py``, ``pre_tool_use_hook.py`` and
    ``subagent_stop_hook.py`` on every allow/block decision (REQ-AUDIT-001).
  * Data Models → ``gate_audit_log`` DDL + "Hash-chain spec" comment block
    (design.md ~1787-1845): canonical form, NULL canonicalization, genesis
    sentinel, seq/created_at client-side pre-assignment protocol.
  * Property 28 — Audit-Log Tamper Detection (Hash Chain): recomputing each
    ``entry_hash`` as ``sha256(canonical_row || prev_hash)`` reproduces every
    stored ``entry_hash``; a broken ``prev_hash`` link fails verification.
Requirements: REQ-AUDIT-001, REQ-AUDIT-002 (Requirement 27 — Tamper-Evident
    Gate-Decision Audit Log), Req 27.4 (producer + callers), Req 27.5
    (hash-chain canonical form).
Task: 52 / 52.1 (this is the producer; 52.2 ``audit_verify.py`` is the verifier).

------------------------------------------------------------------------------
HASH CHAIN
------------------------------------------------------------------------------
Every gate decision is one entry. Each entry stores the hash of the prior
entry (``prev_hash``) so any in-place mutation of an earlier row breaks the
chain at the next ``entry_hash`` recomputation — the chain is tamper-EVIDENT.

    entry_hash = sha256( canonical_row_json + prev_hash )

where ``canonical_row_json`` is the SHARED deterministic JSON serialization of
the eight-key row ``(seq, event_name, tool_name, decision, reason,
requirement_id, actor_agent, created_at)`` and ``prev_hash`` is the prior
entry's ``entry_hash``. The genesis (first) entry uses
``prev_hash = "0" * 64``.

NOTE ON THE GENESIS SENTINEL. This in-memory unit uses ``GENESIS_PREV_HASH =
"0" * 64`` (sixty-four ``0`` hex chars) per the implementer contract for this
component. The Postgres-backed producer/verifier described in design.md use
``sha256("")`` (the empty-string digest) as their documented genesis sentinel.
Both are *documented sentinels of the same length/shape* (64 lowercase hex);
the producer and verifier MUST agree on whichever one they use. ``audit_verify``
for THIS in-memory log re-derives genesis from :data:`GENESIS_PREV_HASH`, so
producer and verifier never diverge. :func:`verify_chain` below is the matching
verifier for this module and reads the same constant.

CANONICALIZATION (design.md "NULL canonicalization" rule). The canonical JSON
ALWAYS emits ALL eight keys (a NULL field is serialized as the JSON ``null``
literal — never ``""``, never key-omission), uses ``sort_keys=True``, ensures
ASCII-safe UTF-8, and uses compact separators (no insignificant whitespace).
:func:`canonical_row` is exported so the verifier imports the SAME function —
otherwise a divergent serialization of a NULL would yield a different
``entry_hash`` and spuriously fail tamper verification.

SEQ / CREATED_AT PROTOCOL (design.md "seq/created_at write protocol"). The
``entry_hash`` INCLUDES ``seq`` and ``created_at``, but ``append(...)`` receives
neither. They are PRE-ASSIGNED client-side: ``seq`` is the next monotonic
integer (1-based) for this log, ``created_at`` is ``now()`` captured in the
client, and the hash is computed over those exact pre-assigned values — so the
stored ``seq``/``created_at`` equal the hashed ones and no post-hash mutation is
ever needed (mirrors the DB ``SELECT nextval(...)`` + client ``now()`` rule).

STORAGE. The unit is backed by an in-memory list. File persistence is OPTIONAL:
pass a ``path`` to mirror each appended entry to a JSONL file (one canonical
entry per line); a DB sink is out of scope for the unit. The in-memory chain is
the source of truth; the file is a durable side-record (append-only JSONL).

This module is PURE STDLIB.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import List, Optional

__all__ = [
    "GENESIS_PREV_HASH",
    "AuditEntry",
    "AuditLog",
    "canonical_row",
    "compute_entry_hash",
    "verify_chain",
]

# Genesis sentinel for THIS in-memory log: sixty-four ``0`` hex characters. The
# first entry's ``prev_hash`` is this constant. (See module docstring for why
# this differs from the DB producer's ``sha256("")`` sentinel — both are valid
# documented sentinels; producer and verifier here share THIS one.)
GENESIS_PREV_HASH = "0" * 64

# The eight canonical-row keys, in their logical (pre-sort) order. The actual
# serialization sorts keys (sort_keys=True), so this tuple is documentation of
# the field set, single-sourced so producer and verifier agree on the columns.
_CANONICAL_KEYS = (
    "seq",
    "event_name",
    "tool_name",
    "decision",
    "reason",
    "requirement_id",
    "actor_agent",
    "created_at",
)

# Allowed gate decisions (mirrors the DDL CHECK (decision IN ('allow','block'))).
_ALLOWED_DECISIONS = ("allow", "block")


@dataclass(frozen=True)
class AuditEntry:
    """One immutable gate-decision audit entry (a row of ``gate_audit_log``).

    Field names mirror the ``gate_audit_log`` DDL columns exactly so a row
    round-trips between this in-memory record, the canonical JSON, and the
    Postgres table without renaming. ``tool_name``, ``reason`` and
    ``requirement_id`` are nullable (``None``); all others are non-null.

    ``seq`` is 1-based and monotonic within a single :class:`AuditLog`.
    ``created_at`` is a timezone-aware RFC-3339 / ISO-8601 string (``+00:00``
    offset) — never naive — so it matches the DDL ``TIMESTAMPTZ`` column and
    re-serializes identically on the verifier side.
    """

    seq: int
    event_name: str
    tool_name: Optional[str]
    decision: str
    reason: Optional[str]
    requirement_id: Optional[str]
    actor_agent: str
    created_at: str
    prev_hash: str
    entry_hash: str


def canonical_row(
    seq: int,
    event_name: str,
    tool_name: Optional[str],
    decision: str,
    reason: Optional[str],
    requirement_id: Optional[str],
    actor_agent: str,
    created_at: str,
) -> bytes:
    """Return the SHARED canonical-row bytes for hashing.

    This is the single canonicalizer that BOTH the producer (:meth:`AuditLog.append`)
    and the verifier (:func:`verify_chain`, and ``tools/audit_verify.py``) MUST
    use, so a NULL field serializes identically on both sides.

    The canonical form is the deterministic JSON of the eight-key row
    ``(seq, event_name, tool_name, decision, reason, requirement_id,
    actor_agent, created_at)`` with:

    * ALL eight keys ALWAYS present (a ``None`` value becomes the JSON ``null``
      literal — never ``""``, never an omitted key);
    * ``sort_keys=True`` (deterministic key order, independent of insertion);
    * compact separators ``(",", ":")`` (no insignificant whitespace);
    * ``ensure_ascii=True`` (stable, ASCII-safe UTF-8 byte output).

    Returns the UTF-8 encoded JSON bytes (``prev_hash``/``entry_hash`` are NOT
    part of the canonical row — they are the chaining/output fields).
    """
    row = {
        "seq": seq,
        "event_name": event_name,
        "tool_name": tool_name,
        "decision": decision,
        "reason": reason,
        "requirement_id": requirement_id,
        "actor_agent": actor_agent,
        "created_at": created_at,
    }
    return json.dumps(
        row,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")


def compute_entry_hash(canonical_row_bytes: bytes, prev_hash: str) -> str:
    """Return ``sha256(canonical_row_json + prev_hash)`` as lowercase hex.

    ``prev_hash`` is concatenated as its UTF-8 bytes after the canonical row
    bytes — the exact ``sha256(canonical_row || prev_hash)`` composition the
    verifier recomputes (Property 28).
    """
    h = hashlib.sha256()
    h.update(canonical_row_bytes)
    h.update(prev_hash.encode("utf-8"))
    return h.hexdigest()


class AuditLog:
    """Append-only, hash-chained gate-decision audit log (in-memory backed).

    The in-memory ``entries`` list is the source of truth. Each
    :meth:`append` chains a new :class:`AuditEntry` onto the prior tip and
    (optionally) mirrors it to a JSONL file. The log is append-only by
    contract: there is no update or delete API (the Postgres table enforces
    the same with a REVOKE + trigger).
    """

    def __init__(self, path: Optional[str] = None) -> None:
        """Create an empty log.

        Parameters
        ----------
        path:
            Optional path to a JSONL file. When given, every appended entry is
            mirrored as one canonical JSON line (the in-memory chain remains
            authoritative). The file is OPENED IN APPEND MODE, so an existing
            file is extended, not truncated — preserving append-only semantics.
            When ``None`` (default) the log is purely in-memory.
        """
        self._entries: List[AuditEntry] = []
        self._path = path

    # -- read API -----------------------------------------------------------

    @property
    def entries(self) -> List[AuditEntry]:
        """A shallow copy of the entries in append order (oldest → newest)."""
        return list(self._entries)

    def __len__(self) -> int:
        return len(self._entries)

    @property
    def tip_hash(self) -> str:
        """The ``entry_hash`` of the most recent entry, or the genesis sentinel.

        For an empty log this is :data:`GENESIS_PREV_HASH` — i.e. the
        ``prev_hash`` the NEXT (first) appended entry will chain onto.
        """
        if not self._entries:
            return GENESIS_PREV_HASH
        return self._entries[-1].entry_hash

    # -- write API ----------------------------------------------------------

    def append(
        self,
        event: str,
        tool: Optional[str],
        decision: str,
        reason: Optional[str],
        requirement_id: Optional[str],
        actor_agent: str,
    ) -> AuditEntry:
        """Append one gate-decision entry and return it.

        Signature matches the spec PRODUCER contract exactly:
        ``append(event, tool, decision, reason, requirement_id, actor_agent)``
        (REQ-AUDIT-001 / Req 27.4). The positional names here (``event``,
        ``tool``) map to the canonical-row / DDL columns ``event_name`` and
        ``tool_name`` respectively.

        ``seq`` and ``created_at`` are PRE-ASSIGNED client-side (see module
        docstring): ``seq`` is the next 1-based monotonic integer for this log,
        ``created_at`` is a timezone-aware ``now()`` ISO-8601 string. The
        ``entry_hash`` is computed over those exact pre-assigned values, so the
        stored row equals the hashed row.

        Parameters
        ----------
        event:
            The gate / hook event name (e.g. ``"Stop"``, ``"PreToolUse"``,
            ``"SubagentStop"``). Non-null.
        tool:
            The tool the decision concerned (e.g. ``"Write"``, ``"Edit"``,
            ``"Bash"``), or ``None`` when no tool applies (e.g. a Stop-hook
            decision). Nullable.
        decision:
            Either ``"allow"`` or ``"block"``. Any other value raises
            ``ValueError`` (mirrors the DDL ``CHECK (decision IN ('allow',
            'block'))``).
        reason:
            Free-text rationale for the decision, or ``None``. Nullable.
        requirement_id:
            The requirement ID the gate decision concerned, or ``None`` (a
            decision may be logged before any requirement is active — e.g. a
            plan-gate or artifact-guard block). Nullable.
        actor_agent:
            The acting agent identity (resolved from runtime signals by
            ``actor_identity.resolve_identity``, never agent-supplied). Non-null.

        Returns
        -------
        AuditEntry
            The newly appended, fully-chained entry.

        Raises
        ------
        ValueError
            If ``decision`` is not ``"allow"`` or ``"block"``, or if a non-null
            required field (``event`` / ``actor_agent``) is empty.
        """
        # Validate the non-null contract up front (fail closed — never silently
        # log a malformed decision). decision is constrained to the DDL CHECK.
        if not event or not isinstance(event, str):
            raise ValueError("audit append requires a non-empty 'event'")
        if not actor_agent or not isinstance(actor_agent, str):
            raise ValueError("audit append requires a non-empty 'actor_agent'")
        if decision not in _ALLOWED_DECISIONS:
            raise ValueError(
                "audit 'decision' must be one of "
                f"{_ALLOWED_DECISIONS!r}, got {decision!r}"
            )

        # Pre-assign seq (1-based, monotonic) and created_at (tz-aware now()).
        seq = len(self._entries) + 1
        created_at = datetime.now(timezone.utc).isoformat()

        # Chain onto the prior tip (genesis sentinel for the first entry).
        prev_hash = self.tip_hash

        row_bytes = canonical_row(
            seq=seq,
            event_name=event,
            tool_name=tool,
            decision=decision,
            reason=reason,
            requirement_id=requirement_id,
            actor_agent=actor_agent,
            created_at=created_at,
        )
        entry_hash = compute_entry_hash(row_bytes, prev_hash)

        entry = AuditEntry(
            seq=seq,
            event_name=event,
            tool_name=tool,
            decision=decision,
            reason=reason,
            requirement_id=requirement_id,
            actor_agent=actor_agent,
            created_at=created_at,
            prev_hash=prev_hash,
            entry_hash=entry_hash,
        )
        self._entries.append(entry)
        self._mirror_to_file(entry)
        return entry

    # -- verification -------------------------------------------------------

    def verify_chain(self) -> bool:
        """Walk this log's entries and return ``True`` iff the chain is intact.

        Re-derives the chain from the genesis sentinel, asserting for every
        entry that:

        * its stored ``prev_hash`` equals the prior entry's ``entry_hash``
          (the genesis sentinel for the first entry);
        * its stored ``entry_hash`` equals the recomputed
          ``sha256(canonical_row || prev_hash)`` over its own fields; and
        * its ``seq`` is the expected 1-based monotonic value.

        An EMPTY chain returns ``True`` (a no-decision log is trivially
        consistent); a GENESIS-ONLY chain returns ``True``. Any broken link,
        tampered row, or out-of-order ``seq`` returns ``False``.

        Thin instance wrapper over the module-level :func:`verify_chain`, which
        is the same function ``tools/audit_verify.py`` reuses.
        """
        return verify_chain(self._entries)

    # -- internals ----------------------------------------------------------

    def _mirror_to_file(self, entry: AuditEntry) -> None:
        """Append one entry as a canonical JSON line to the optional JSONL file.

        No-op when ``path`` was not supplied. The file is the durable side-
        record; the in-memory chain stays authoritative. Written in append mode
        so the file is never truncated.
        """
        if self._path is None:
            return
        line = json.dumps(
            asdict(entry),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )
        # Append a single line; create the file if missing.
        with open(self._path, "a", encoding="utf-8") as fh:
            fh.write(line + os.linesep)


def verify_chain(entries: List[AuditEntry]) -> bool:
    """Recompute the hash chain over ``entries`` and return pass/fail.

    Module-level verifier — the same routine :meth:`AuditLog.verify_chain`
    delegates to and that an external ``tools/audit_verify.py`` can import. It
    mirrors the producer's canonical form by reusing :func:`canonical_row` and
    :func:`compute_entry_hash`, so a NULL field never serializes differently
    between producer and verifier (the divergence that would otherwise
    spuriously fail tamper verification).

    Parameters
    ----------
    entries:
        The ordered list of :class:`AuditEntry` (oldest → newest), as produced
        by :class:`AuditLog`. The list is re-sorted by ``seq`` defensively so
        an out-of-order input is still walked in chain order.

    Returns
    -------
    bool
        ``True`` iff every entry's ``prev_hash`` links to the prior entry's
        recomputed ``entry_hash`` (genesis sentinel for the first), every
        ``entry_hash`` recomputes correctly, and ``seq`` is the expected 1-based
        monotonic sequence. ``True`` for an empty list and a genesis-only list.
    """
    prev = GENESIS_PREV_HASH
    for expected_seq, entry in enumerate(
        sorted(entries, key=lambda e: e.seq), start=1
    ):
        # seq must be the expected 1-based monotonic value (a dropped or
        # duplicated row would break this even before the hash check).
        if entry.seq != expected_seq:
            return False

        # prev_hash must point at the prior entry's recomputed entry_hash.
        if entry.prev_hash != prev:
            return False

        # entry_hash must recompute from this entry's own canonical row + prev.
        row_bytes = canonical_row(
            seq=entry.seq,
            event_name=entry.event_name,
            tool_name=entry.tool_name,
            decision=entry.decision,
            reason=entry.reason,
            requirement_id=entry.requirement_id,
            actor_agent=entry.actor_agent,
            created_at=entry.created_at,
        )
        recomputed = compute_entry_hash(row_bytes, entry.prev_hash)
        if entry.entry_hash != recomputed:
            return False

        prev = entry.entry_hash

    return True
