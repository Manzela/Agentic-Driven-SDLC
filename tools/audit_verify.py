"""audit_verify.py — gate_audit_log hash-chain VERIFIER (REQ-AUDIT-002/003).

Spec: .kiro/specs/spec-to-evidence-control/design.md
  * Component Inventory row ``audit_verify.py`` (Phase 3): "Recomputes the
    ``gate_audit_log`` hash chain; on-demand verifier plus the merge-time CI
    required check (REQ-AUDIT-002/003)."
  * "Audit-Chain Verifier (``audit_verify.py``)" subsection (design.md
    ~1336-1358): the ``verify_chain(rows) -> Result`` signature, the
    recomputation rule, the genesis sentinel, the edge cases, and the
    fail-CLOSED error-handling contract.
  * Property 28 — Audit-Log Tamper Detection (Hash Chain): recomputing each
    ``entry_hash`` as ``sha256(canonical_row || prev_hash)`` (genesis
    ``prev_hash = sha256("")``) reproduces every stored ``entry_hash``; any row
    whose ``prev_hash`` does not equal the recomputed digest of the prior row
    fails verification.
Requirements: REQ-AUDIT-002 (on-demand chain verification) / REQ-AUDIT-003
    (merge-time required CI status check). Requirement 27 — Tamper-Evident
    Gate-Decision Audit Log.
Task: 52 / 52.2 (the VERIFIER; 52.1 ``tools/audit_log.py`` is the producer).

------------------------------------------------------------------------------
WHAT THIS VERIFIES
------------------------------------------------------------------------------
The ``gate_audit_log`` is an append-only, hash-chained log of every allow/block
gate decision. Each row stores ``prev_hash`` (the prior row's ``entry_hash``)
so any in-place mutation of an earlier row breaks the chain at the next
``entry_hash`` recomputation. This module RE-WALKS a set of rows and proves the
chain is intact:

    entry_hash == sha256( canonical_row || prev_hash )                (row OK)
    row.prev_hash == prior_row.entry_hash                       (link intact)

``canonical_row`` is the SHARED deterministic JSON of the eight-key row
``(seq, event_name, tool_name, decision, reason, requirement_id, actor_agent,
created_at)``. This module IMPORTS that single canonicalizer from
``tools.audit_log`` (design.md ~1820-1823: "audit_log.py and audit_verify.py
MUST import ONE shared canonicalizer function so producer and verifier
serialize NULL identically — otherwise a divergent serialization would yield a
different entry_hash and spuriously fail tamper verification"). A NULL field
(``tool_name`` / ``reason`` / ``requirement_id``) is therefore serialized as
the JSON ``null`` literal on both sides — never ``""``, never key-omission.

------------------------------------------------------------------------------
GENESIS SENTINEL
------------------------------------------------------------------------------
design.md pins the DB-backed log's genesis sentinel as ``sha256("")`` — the
empty-string digest (design.md line 1797 / 1814 / Property 28 line 1678). That
is this verifier's DEFAULT, because it verifies ``gate_audit_log`` rows emitted
by the Postgres-backed producer described in the DDL.

The sibling in-memory producer ``tools/audit_log.AuditLog`` documents a
DIFFERENT-but-equally-valid sentinel (``GENESIS_PREV_HASH = "0" * 64``); see
that module's docstring. Both are 64-lowercase-hex sentinels and producer/
verifier MUST agree on whichever they use. So :func:`verify_chain` accepts a
``genesis_prev_hash`` override, and :data:`GENESIS_SENTINELS` enumerates the
two documented sentinels so a chain produced by EITHER producer can be verified
without the caller having to know which one minted it (the ``genesis`` kwarg
``None`` default auto-selects whichever documented sentinel the first row's
``prev_hash`` matches, falling back to the design.md ``sha256("")`` default).

------------------------------------------------------------------------------
RESULT CONTRACT (this module's public verify_chain)
------------------------------------------------------------------------------
``verify_chain(entries: list[dict]) -> dict`` returns::

    {"ok": bool, "broken_at": int | None, "count": int}

  * ``ok``        — True iff every link and every entry_hash recomputes.
  * ``broken_at`` — the 0-based INDEX (into the seq-ordered walk) of the FIRST
                    broken row, or ``None`` when ``ok`` is True.
  * ``count``     — the number of rows walked.

Two diagnostic keys are also present (``broken_seq``, ``why``) for operators /
CI logs; they are additive and never change the three-key core contract above.
An EMPTY chain and a GENESIS-ONLY chain both verify ``{"ok": True,
"broken_at": None, "count": N}`` (design.md edge-cases line 1356).

------------------------------------------------------------------------------
CLI / FAIL-CLOSED
------------------------------------------------------------------------------
``python3 tools/audit_verify.py [chain.jsonl ...]`` reads the chain (from JSONL
file args, or stdin when none are given), verifies it, and EXITS NON-ZERO on a
broken chain — this is the merge-time REQUIRED CI status check (REQ-AUDIT-003).
Per the never-fail-open rule (design.md line 1357 / 1379) an UNREADABLE or
un-recomputable chain also FAILS (fail CLOSED, distinct non-zero exit) — an
unverifiable chain is never reported as passing.

This module is PURE STDLIB.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from typing import Any, Dict, List, Mapping, Optional, Sequence

# Make the repo root importable so the shared-canonicalizer import below
# resolves under BOTH entry paths: `from tools.audit_verify import ...` (pytest /
# importable use, repo root already on sys.path) AND direct on-demand execution
# `python3 tools/audit_verify.py` (design.md line 1358), where the script's OWN
# directory — not the repo root — is on sys.path, so the `tools` package is
# otherwise unresolvable. Idempotent: a no-op when the root is already present.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

# Reuse the SHARED canonicalizer + hasher from the producer so a NULL field
# serializes identically on both sides (design.md ~1820-1823). This is the
# load-bearing import: re-implementing canonicalization here would risk a
# divergent NULL serialization and a spurious tamper failure. The import sits
# AFTER the sys.path bootstrap above (so direct script execution can resolve the
# `tools` package), hence the E402 suppression — the same import-after-path
# pattern the repo's tests/spine/test_state_integrity.py already uses.
from tools.audit_log import (  # noqa: E402
    GENESIS_PREV_HASH as _ZERO_GENESIS,  # the in-memory log's "0"*64 sentinel
    canonical_row,
    compute_entry_hash,
)

__all__ = [
    "DEFAULT_GENESIS_PREV_HASH",
    "GENESIS_SENTINELS",
    "EXIT_OK",
    "EXIT_BROKEN",
    "EXIT_UNREADABLE",
    "verify_chain",
    "verify_rows",
    "load_entries",
    "main",
]

# design.md genesis sentinel for the DB-backed gate_audit_log: sha256("") —
# the empty-string digest (DDL line 1797 / hash-chain spec line 1814 /
# Property 28 line 1678). This is the DEFAULT genesis for this verifier.
DEFAULT_GENESIS_PREV_HASH = hashlib.sha256(b"").hexdigest()

# The two DOCUMENTED genesis sentinels a chain may legitimately begin with:
#   * sha256("")  — the design.md / DB producer sentinel (default here);
#   * "0" * 64    — the in-memory tools/audit_log.AuditLog sentinel.
# Both are 64-lowercase-hex; with genesis=None the verifier auto-selects the
# one the first row's prev_hash matches (so it can verify a chain from EITHER
# producer), defaulting to DEFAULT_GENESIS_PREV_HASH otherwise.
GENESIS_SENTINELS = (DEFAULT_GENESIS_PREV_HASH, _ZERO_GENESIS)

# CLI exit codes. 0 = chain verified; 1 = a broken/tampered chain (the merge
# gate must fail); 2 = unreadable/un-recomputable input (fail CLOSED — never
# report an unverifiable chain as passing).
EXIT_OK = 0
EXIT_BROKEN = 1
EXIT_UNREADABLE = 2

# The eight canonical-row fields the entry_hash is computed over. A row dict
# (or object) must expose every one of these. Single-sourced from the producer's
# canonical_row signature so the field set never drifts between the two modules.
_CANONICAL_FIELDS = (
    "seq",
    "event_name",
    "tool_name",
    "decision",
    "reason",
    "requirement_id",
    "actor_agent",
    "created_at",
)


class ChainUnreadable(Exception):
    """A chain row is missing a hash-chain field or cannot be recomputed.

    Raised by :func:`verify_chain` (and propagated by :func:`verify_rows`) when
    a row lacks one of the eight canonical fields, ``prev_hash``, or
    ``entry_hash`` — i.e. the chain is not even SHAPED like a gate_audit_log
    chain and so is UNVERIFIABLE (distinct from a well-formed-but-tampered
    chain). The CLI maps this to the fail-CLOSED exit code, never to "ok".
    """


def _field(row: Mapping[str, Any] | Any, name: str) -> Any:
    """Read ``name`` from a row given as a dict OR an object (e.g. AuditEntry).

    The public contract is ``list[dict]`` (gate_audit_log rows), but the same
    walk is reused by :meth:`tools.audit_log.AuditLog`-style ``AuditEntry``
    dataclasses, so a non-mapping row is read by attribute. A missing field is
    a chain-unreadable condition, not a tamper, so it raises
    :class:`ChainUnreadable`.
    """
    if isinstance(row, Mapping):
        if name not in row:
            raise ChainUnreadable(f"row missing required field {name!r}")
        return row[name]
    try:
        return getattr(row, name)
    except AttributeError as exc:  # pragma: no cover - defensive
        raise ChainUnreadable(f"row missing required field {name!r}") from exc


def _row_canonical_bytes(row: Mapping[str, Any] | Any) -> bytes:
    """Return the SHARED canonical-row bytes for ``row`` via the producer's func.

    Pulls the eight canonical fields off the row (dict or object) and feeds them
    to the imported :func:`tools.audit_log.canonical_row` — the single
    canonicalizer the producer used — so NULL serialization is identical.
    """
    values = {name: _field(row, name) for name in _CANONICAL_FIELDS}
    return canonical_row(
        seq=values["seq"],
        event_name=values["event_name"],
        tool_name=values["tool_name"],
        decision=values["decision"],
        reason=values["reason"],
        requirement_id=values["requirement_id"],
        actor_agent=values["actor_agent"],
        created_at=values["created_at"],
    )


def _select_genesis(rows: Sequence[Any]) -> str:
    """Choose the genesis sentinel to walk ``rows`` from (auto-detect path).

    When the caller passes ``genesis=None`` we auto-select: if the first row's
    ``prev_hash`` matches one of the two DOCUMENTED sentinels
    (:data:`GENESIS_SENTINELS`) we adopt that one, so a chain from EITHER the
    DB producer (``sha256("")``) or the in-memory producer (``"0"*64``) is
    verifiable without the caller naming which minted it. Otherwise we fall
    back to the design.md default (``sha256("")``) and let the normal link
    check report the mismatch as the (genesis) break.
    """
    if not rows:
        return DEFAULT_GENESIS_PREV_HASH
    try:
        first_prev = _field(rows[0], "prev_hash")
    except ChainUnreadable:
        return DEFAULT_GENESIS_PREV_HASH
    if first_prev in GENESIS_SENTINELS:
        return first_prev
    return DEFAULT_GENESIS_PREV_HASH


def verify_chain(
    entries: List[Dict[str, Any]],
    *,
    genesis: Optional[str] = None,
) -> Dict[str, Any]:
    """Verify a ``gate_audit_log`` hash chain; return the Result dict.

    Walks ``entries`` in ``seq`` order (the rows are sorted by ``seq``
    defensively, so an out-of-order input is still verified in chain order —
    design.md walks "rows ordered by seq", backed by the BIGSERIAL PRIMARY KEY)
    and recomputes the chain from the genesis sentinel. For each row it asserts:

      * ``prev_hash`` equals the prior row's recomputed ``entry_hash`` (the
        genesis sentinel for the first row); and
      * the stored ``entry_hash`` equals ``sha256(canonical_row || prev_hash)``
        recomputed over the row's own eight canonical fields.

    Verification FAILS at the FIRST row whose link or ``entry_hash`` does not
    recompute (Property 28 / design.md pseudocode lines 1345-1353).

    Parameters
    ----------
    entries:
        The ``gate_audit_log`` rows as dicts (each carrying the eight canonical
        fields plus ``prev_hash`` and ``entry_hash``). ``AuditEntry``-style
        objects are also accepted (fields read by attribute).
    genesis:
        Genesis sentinel for the first row's ``prev_hash``. ``None`` (default)
        AUTO-SELECTS between the two documented sentinels (see
        :func:`_select_genesis`); pass an explicit 64-hex string to pin one
        (e.g. ``DEFAULT_GENESIS_PREV_HASH`` for the DB log, or
        ``GENESIS_PREV_HASH`` from ``tools.audit_log`` for the in-memory log).

    Returns
    -------
    dict
        ``{"ok": bool, "broken_at": int | None, "count": int,
        "broken_seq": int | None, "why": str | None}``. ``broken_at`` is the
        0-based index of the first broken row (``None`` when ``ok``); the
        ``broken_seq``/``why`` keys are additive diagnostics. An EMPTY chain and
        a GENESIS-ONLY chain both return ``ok=True``.

    Raises
    ------
    ChainUnreadable
        If a row is missing a canonical field, ``prev_hash``, or ``entry_hash``
        — the chain is un-recomputable (fail CLOSED at the CLI), NOT a tamper.
    """
    rows = list(entries)
    count = len(rows)

    # Defensive seq-ordered walk (PRIMARY KEY order in the DB). A row missing
    # ``seq`` is unreadable, surfaced by _field via the sort key.
    ordered = sorted(rows, key=lambda r: _field(r, "seq"))

    prev = _select_genesis(ordered) if genesis is None else genesis

    for index, row in enumerate(ordered):
        stored_prev = _field(row, "prev_hash")
        stored_entry = _field(row, "entry_hash")

        # Recompute this row's entry_hash from its OWN canonical fields chained
        # onto its OWN stored prev_hash (so a tampered field is caught here),
        # AND independently check the LINK to the prior recomputed hash.
        recomputed = compute_entry_hash(_row_canonical_bytes(row), stored_prev)

        if stored_prev != prev:
            # The chain link is broken: this row does not point at the prior
            # row's (recomputed) entry_hash — the genesis sentinel for row 0.
            return {
                "ok": False,
                "broken_at": index,
                "count": count,
                "broken_seq": _field(row, "seq"),
                "why": "prev_hash mismatch",
            }

        if stored_entry != recomputed:
            # The row itself was tampered: its stored entry_hash no longer
            # equals the hash of its own canonical row + prev_hash.
            return {
                "ok": False,
                "broken_at": index,
                "count": count,
                "broken_seq": _field(row, "seq"),
                "why": "entry_hash mismatch",
            }

        # Advance the chain by this row's (verified) entry_hash. Use the
        # recomputed value — identical to stored here since it matched — so the
        # next link is checked against a re-derived hash, not a trusted one.
        prev = recomputed

    return {
        "ok": True,
        "broken_at": None,
        "count": count,
        "broken_seq": None,
        "why": None,
    }


def verify_rows(
    entries: List[Dict[str, Any]],
    *,
    genesis: Optional[str] = None,
) -> bool:
    """Boolean convenience wrapper over :func:`verify_chain`.

    Returns ``True`` iff the chain verifies. A :class:`ChainUnreadable` chain is
    treated as a FAILURE (``False``) — fail CLOSED, never report an
    unverifiable chain as passing (design.md line 1357).
    """
    try:
        return bool(verify_chain(entries, genesis=genesis)["ok"])
    except ChainUnreadable:
        return False


# --------------------------------------------------------------------------- #
# CLI                                                                          #
# --------------------------------------------------------------------------- #


def load_entries(text: str) -> List[Dict[str, Any]]:
    """Parse chain rows from JSON text (a JSON array OR JSONL).

    Accepts either a single JSON ARRAY of row objects, or JSON-LINES (one row
    object per non-blank line — the format ``AuditLog`` mirrors to disk). A
    parse error or a non-object row raises :class:`ChainUnreadable` so the CLI
    fails CLOSED rather than silently verifying an empty/garbage chain.
    """
    stripped = text.strip()
    if not stripped:
        return []

    rows: List[Dict[str, Any]]
    if stripped[0] == "[":
        try:
            loaded = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise ChainUnreadable(f"chain is not valid JSON: {exc}") from exc
        if not isinstance(loaded, list):
            raise ChainUnreadable("top-level JSON must be an array of rows")
        rows = loaded
    else:
        rows = []
        for lineno, line in enumerate(stripped.splitlines(), start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ChainUnreadable(
                    f"line {lineno} is not valid JSON: {exc}"
                ) from exc

    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ChainUnreadable(f"row {i} is not a JSON object")
    return rows


def _read_sources(paths: Sequence[str]) -> str:
    """Read and concatenate chain text from file paths, or stdin when empty.

    A missing/unreadable file is a fail-CLOSED condition surfaced as
    :class:`ChainUnreadable`.
    """
    if not paths:
        return sys.stdin.read()
    chunks: List[str] = []
    for path in paths:
        try:
            with open(path, encoding="utf-8") as fh:
                chunks.append(fh.read())
        except OSError as exc:
            raise ChainUnreadable(f"cannot read chain file {path!r}: {exc}") from exc
    return "\n".join(chunks)


def main(argv: Optional[Sequence[str]] = None) -> int:
    """CLI entry point — the merge-time required check (REQ-AUDIT-002/003).

    Reads the chain (from JSONL/JSON file args, or stdin when none given),
    verifies it, prints a one-line JSON Result to stdout, and RETURNS an exit
    code:

      * :data:`EXIT_OK` (0)         — chain verified;
      * :data:`EXIT_BROKEN` (1)     — a broken/tampered link (the gate fails);
      * :data:`EXIT_UNREADABLE` (2) — chain unreadable/un-recomputable (fail
        CLOSED — an unverifiable chain is NEVER reported as passing).

    Returns the exit code (the ``if __name__`` block passes it to
    :func:`sys.exit`), so a broken chain exits NON-ZERO as the required check.
    """
    parser = argparse.ArgumentParser(
        prog="audit_verify",
        description=(
            "Verify the gate_audit_log hash chain (REQ-AUDIT-002/003). "
            "Exits non-zero on a broken or unreadable chain (fail closed)."
        ),
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help="Chain file(s) as a JSON array or JSONL of rows; stdin if omitted.",
    )
    parser.add_argument(
        "--genesis",
        default=None,
        help=(
            "Override the genesis prev_hash sentinel (64-hex). Default "
            "auto-selects between sha256('') and '0'*64."
        ),
    )
    args = parser.parse_args(argv)

    try:
        entries = load_entries(_read_sources(args.paths))
        result = verify_chain(entries, genesis=args.genesis)
    except ChainUnreadable as exc:
        # Fail CLOSED: an unreadable/un-recomputable chain is never "ok".
        print(
            json.dumps(
                {
                    "ok": False,
                    "broken_at": None,
                    "count": None,
                    "broken_seq": None,
                    "why": f"unreadable: {exc}",
                }
            )
        )
        return EXIT_UNREADABLE

    # Emit only the public three-key contract plus the diagnostics, in a
    # stable, machine-parseable single line for CI logs.
    print(
        json.dumps(
            {
                "ok": result["ok"],
                "broken_at": result["broken_at"],
                "count": result["count"],
                "broken_seq": result.get("broken_seq"),
                "why": result.get("why"),
            }
        )
    )
    return EXIT_OK if result["ok"] else EXIT_BROKEN


if __name__ == "__main__":
    sys.exit(main())
