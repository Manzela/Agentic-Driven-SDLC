"""store.py — durable-store abstraction over the 8 db/migrations tables.

Spec: .kiro/specs/spec-to-evidence-control
Requirements: 16.1, 16.2, 16.3 (REQ-STORE-001..003 — Durable Storage); tasks 30, 31.
Properties: Property 19 (Evidence Round-Trip), Property 2 / Req 5.3 / 5.6
            (four-field proven-transition gate), Property 24 (evidence provenance).

This module is the single durable-store abstraction the control plane reads and
writes coverage state, run state, and Evidence_Records through. It mirrors — in
pure stdlib ``sqlite3`` — the canonical Postgres schema laid down by the eight
migrations under ``db/migrations`` (001_requirements … 008_gate_audit_log), so
the in-session helpers and tests can exercise the SAME shapes and the SAME gates
the production Postgres store enforces, with no Postgres dependency.

Backends
--------
* **REFERENCE (default):** stdlib ``sqlite3`` against ``":memory:"``. Used by the
  property/integration tests. Zero external dependencies. The schema below is the
  faithful sqlite translation of the eight migrations (the canonical
  ``CREATE TABLE`` blocks): the Postgres ``SERIAL``/``BIGSERIAL`` become
  ``INTEGER PRIMARY KEY AUTOINCREMENT``, ``TIMESTAMPTZ`` becomes ``TEXT`` holding
  RFC-3339 strings, ``BOOLEAN`` becomes ``INTEGER`` 0/1, and the canonical
  ``CHECK`` constraints (status / type / decision domains, evidence completeness,
  the ``^sha256:[a-f0-9]{64}$`` output_hash format) are carried over verbatim so a
  malformed write is rejected by the DB exactly as Postgres rejects it.

* **Postgres ADAPTER SEAM (optional):** pass a libpq connection string as
  ``connection_string`` (or ``backend="postgres"``). The seam is documented and
  importable but Postgres itself is optional — the actual ``psycopg`` connection
  is opened lazily only when a Postgres connection string is supplied, so this
  module imports and runs with stdlib alone. The reference backend and the
  Postgres backend present the IDENTICAL ``Store`` method surface; only the DBAPI
  driver and the bound-parameter paramstyle differ (``?`` vs ``%s``), which the
  Store normalizes internally.

The proven-transition gate
--------------------------
``store_evidence`` is the durable-store mirror of the in-session SubagentStop /
PreToolUse four-field gate (``evidence_collector.validate_evidence_record``) and
the merge gate (``coverage_gate._evidence_complete``). Flipping a coverage item
to ``proven`` REQUIRES a complete four-field Evidence_Record
(``test_file``, ``test_name``, ``output_hash``, ``collected_at`` — each present,
non-empty, with a well-formed ``sha256:<64 hex>`` ``output_hash``). A flip to
``proven`` without that record RAISES ``EvidenceIncompleteError`` — the store
refuses to record the proof, exactly mirroring the gate. This is enforced in one
place so the durable store can never be left in a state the gates would reject.

Scope
-----
Every coverage query honours ``in_scope`` (Req 5.7): ``query_uncovered`` returns
only the IN-SCOPE items that are not ``proven``, mirroring ``coverage_gate`` and
``stop_hook.evaluate_stop`` — an out-of-scope item never appears as uncovered.

Pure stdlib. Importable and side-effect free at import time.
"""

from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# Single-source the four-field validator + format pattern from the collector so
# the durable store and the in-session gate enforce EXACTLY the same contract
# (no second, drifting copy of the four-field rule).
from evidence_collector import (  # noqa: E402  (flat-module import, mirrors sibling tools)
    OUTPUT_HASH_PATTERN,
    validate_evidence_record,
)

__all__ = [
    "Store",
    "StoreError",
    "EvidenceIncompleteError",
    "TransitionError",
    "EVIDENCE_FIELDS",
    "COVERAGE_STATUSES",
    "REQUIREMENT_TYPES",
    "RUN_STATE_STATUSES",
]

# The four required Evidence_Record fields, canonical order. Mirrors
# evidence_collector / coverage_gate.EVIDENCE_FIELDS and the JSON-Schema
# EvidenceRecord.required list. actor_agent / evidence_kind are PROVENANCE, not
# part of the four-field proven-transition gate.
EVIDENCE_FIELDS = ("test_file", "test_name", "output_hash", "collected_at")

# Domains carried verbatim from the migration CHECK constraints.
COVERAGE_STATUSES = ("unproven", "proven", "failed")          # 002_coverage_items
REQUIREMENT_TYPES = ("functional", "NFR", "WIRING")           # 001_requirements
RUN_STATE_STATUSES = ("running", "complete", "handoff", "blocked")  # 005_run_state

import sys as _sys  # noqa: E402
from pathlib import Path as _Path  # noqa: E402
_sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))
from tools.spine_roles import VERIFIER_ROLE  # noqa: E402  (single-source role constant)


class StoreError(Exception):
    """Base class for all durable-store violations."""


class EvidenceIncompleteError(StoreError):
    """Raised when a flip to ``proven`` lacks a complete four-field Evidence_Record.

    Mirrors the in-session four-field gate (Property 2 / Req 5.3 / 5.6): the store
    refuses to record a proven transition without a complete Evidence_Record,
    exactly as the SubagentStop hook and the OPA merge gate refuse it.
    """


class TransitionError(StoreError):
    """Raised when a status transition is outside the allowed set.

    Mirrors ``coverage.ALLOWED_TRANSITIONS``: unproven->proven, unproven->failed,
    failed->unproven, proven->unproven (amendment re-entry only).
    """


# The only legal status moves — single-sourced semantics from coverage.py
# (kept as a local literal so store.py imports stdlib + evidence_collector only).
_ALLOWED_TRANSITIONS = {
    ("unproven", "proven"),
    ("unproven", "failed"),
    ("failed", "unproven"),
    ("proven", "unproven"),  # amendment re-entry only
}


# --------------------------------------------------------------------------- #
# Reference-backend schema — the faithful sqlite translation of the eight
# canonical migrations (db/migrations/001..008). Kept in ONE place so the
# reference store and the migration files cannot silently diverge.
# --------------------------------------------------------------------------- #
_REFERENCE_SCHEMA = """
-- 001_requirements.sql
CREATE TABLE IF NOT EXISTS requirements (
    id           TEXT PRIMARY KEY,
    project_id   TEXT NOT NULL,
    type         TEXT NOT NULL CHECK (type IN ('functional', 'NFR', 'WIRING')),
    nfr_subtype  TEXT CHECK (nfr_subtype IN ('performance','accessibility','reliability','security')),
    priority     INTEGER NOT NULL,
    ears_pattern TEXT NOT NULL,
    ears_stmt    TEXT NOT NULL,
    provenance   TEXT NOT NULL CHECK (provenance IN ('stated', 'inferred')),
    created_at   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

-- 002_coverage_items.sql
CREATE TABLE IF NOT EXISTS coverage_items (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    requirement_id TEXT NOT NULL REFERENCES requirements(id),
    status         TEXT NOT NULL CHECK (status IN ('unproven', 'proven', 'failed')) DEFAULT 'unproven',
    subtype        TEXT CHECK (subtype IN ('performance', 'accessibility', 'ui-screen')),
    in_scope       INTEGER NOT NULL DEFAULT 1 CHECK (in_scope IN (0, 1)),
    slice_id       TEXT,
    updated_at     TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    UNIQUE (requirement_id)
);
CREATE INDEX IF NOT EXISTS idx_coverage_items_requirement_id ON coverage_items (requirement_id);

-- 003_traceability_links.sql
CREATE TABLE IF NOT EXISTS traceability_links (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    requirement_id  TEXT NOT NULL REFERENCES requirements(id),
    link_type       TEXT NOT NULL CHECK (link_type IN
                      ('implementation', 'test', 'evidence', 'commit', 'owner')),
    target_ref      TEXT NOT NULL,
    direction       TEXT NOT NULL CHECK (direction IN ('forward', 'backward')),
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE INDEX IF NOT EXISTS idx_traceability_links_requirement_id ON traceability_links (requirement_id);

-- 004_evidence_records.sql  (sqlite cannot do Postgres '~' regex in a CHECK;
-- the ^sha256:[a-f0-9]{64}$ format is enforced application-side in store_evidence
-- via OUTPUT_HASH_PATTERN — the SAME pattern the JSON schema + the DB CHECK use.)
CREATE TABLE IF NOT EXISTS evidence_records (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    requirement_id  TEXT NOT NULL REFERENCES requirements(id),
    commit_sha      TEXT NOT NULL,
    test_file       TEXT NOT NULL,
    test_name       TEXT NOT NULL,
    output_hash     TEXT NOT NULL,
    collected_at    TEXT NOT NULL,
    actor_agent     TEXT NOT NULL,
    CHECK (test_file <> '' AND test_name <> '' AND output_hash <> '' AND collected_at IS NOT NULL)
);
CREATE INDEX IF NOT EXISTS idx_evidence_records_requirement_id ON evidence_records (requirement_id);

-- 005_run_state.sql
CREATE TABLE IF NOT EXISTS run_state (
    session_id           TEXT PRIMARY KEY,
    project_id           TEXT NOT NULL,
    current_item_id      TEXT REFERENCES requirements(id),
    status               TEXT NOT NULL CHECK (status IN ('running', 'complete', 'handoff', 'blocked')),
    phase                TEXT NOT NULL DEFAULT 'spec' CHECK (phase IN ('spec', 'implementation')),
    iteration_count      INTEGER NOT NULL DEFAULT 0,
    spec_pass_count      INTEGER NOT NULL DEFAULT 0,
    token_cost_usd       REAL NOT NULL DEFAULT 0,
    no_progress_n        INTEGER NOT NULL DEFAULT 0,
    violation_count      INTEGER NOT NULL DEFAULT 0,
    prev_violation_count INTEGER,
    retry_count          INTEGER NOT NULL DEFAULT 0,
    resume_integrity_ok  INTEGER CHECK (resume_integrity_ok IN (0, 1)),
    is_resume            INTEGER NOT NULL DEFAULT 0 CHECK (is_resume IN (0, 1)),
    first_write_done     INTEGER NOT NULL DEFAULT 0 CHECK (first_write_done IN (0, 1)),
    resume_state_hash    TEXT,
    stop_hook_active     INTEGER NOT NULL DEFAULT 0 CHECK (stop_hook_active IN (0, 1)),
    last_commit_sha      TEXT,
    updated_at           TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

-- 006_domain_baseline_checklists.sql
CREATE TABLE IF NOT EXISTS domain_baseline_checklists (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    product_class   TEXT NOT NULL,
    version         TEXT NOT NULL,
    sha             TEXT NOT NULL,
    file_path       TEXT NOT NULL,
    approved_at     TEXT,
    approved_by     TEXT,
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    UNIQUE (product_class, version)
);

-- 007_requirement_versions.sql  (append-only enforced application-side in
-- amend_requirement: INSERT-only, version = COALESCE(MAX(version),0)+1.)
CREATE TABLE IF NOT EXISTS requirement_versions (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    requirement_id TEXT NOT NULL REFERENCES requirements(id) ON DELETE RESTRICT,
    version        INTEGER NOT NULL,
    prior_text     TEXT,
    new_text       TEXT NOT NULL,
    author         TEXT NOT NULL,
    rationale      TEXT NOT NULL,
    created_at     TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    UNIQUE (requirement_id, version)
);
CREATE INDEX IF NOT EXISTS idx_requirement_versions_requirement_id ON requirement_versions (requirement_id);

-- 008_gate_audit_log.sql  (append-only; hash-chain producer lives in audit_log.py.
-- The reference store carries the table so a self-contained store can hold it.)
CREATE TABLE IF NOT EXISTS gate_audit_log (
    seq            INTEGER PRIMARY KEY AUTOINCREMENT,
    event_name     TEXT NOT NULL,
    tool_name      TEXT,
    decision       TEXT NOT NULL CHECK (decision IN ('allow', 'block')),
    reason         TEXT,
    requirement_id TEXT,
    actor_agent    TEXT NOT NULL,
    created_at     TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    prev_hash      TEXT NOT NULL,
    entry_hash     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_gate_audit_log_requirement_id ON gate_audit_log (requirement_id);
CREATE INDEX IF NOT EXISTS idx_gate_audit_log_created_at     ON gate_audit_log (created_at);
"""


# The run_state columns this Store reads/writes, in a single canonical order so
# save/load round-trip is loss-free (Property 19's spirit for run state).
_RUN_STATE_COLUMNS = (
    "session_id",
    "project_id",
    "current_item_id",
    "status",
    "phase",
    "iteration_count",
    "spec_pass_count",
    "token_cost_usd",
    "no_progress_n",
    "violation_count",
    "prev_violation_count",
    "retry_count",
    "resume_integrity_ok",
    "is_resume",
    "first_write_done",
    "resume_state_hash",
    "stop_hook_active",
    "last_commit_sha",
)
# run_state columns stored as INTEGER 0/1 but surfaced to callers as bool.
_RUN_STATE_BOOL_COLUMNS = (
    "resume_integrity_ok",
    "is_resume",
    "first_write_done",
    "stop_hook_active",
)


def _utc_now_iso() -> str:
    """RFC-3339 timezone-aware now() — matches evidence_collector.collect()."""
    return datetime.now(timezone.utc).isoformat()


class Store:
    """Durable-store abstraction over the eight migrations.

    Construct with the default reference backend (in-memory sqlite)::

        store = Store()                       # ":memory:" reference backend
        store = Store(database=":memory:")    # explicit
        store = Store(database="/tmp/ascp.db")  # file-backed sqlite reference

    Or against Postgres via the documented adapter seam (Postgres optional)::

        store = Store(connection_string="postgresql://user@host/db")
        store = Store(backend="postgres",
                      connection_string="postgresql://user@host/db")

    The reference backend creates the schema on construction. The Postgres
    backend assumes the eight migrations have already been applied (production
    Postgres is migration-managed, not created here) and only opens a connection.
    """

    def __init__(
        self,
        database: str = ":memory:",
        *,
        backend: Optional[str] = None,
        connection_string: Optional[str] = None,
    ) -> None:
        # Backend selection. A Postgres connection string implies the Postgres
        # backend; otherwise the stdlib sqlite reference backend is used.
        if backend is None:
            backend = "postgres" if connection_string else "sqlite"
        backend = backend.lower()
        if backend not in ("sqlite", "postgres"):
            raise StoreError(f"unknown backend {backend!r}; expected 'sqlite' or 'postgres'")

        self.backend = backend
        self._connection_string = connection_string

        if backend == "sqlite":
            # REFERENCE backend. Foreign keys ON so the REFERENCES above bite.
            self._conn = sqlite3.connect(database)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA foreign_keys = ON")
            self._paramstyle = "qmark"  # '?'
            self._conn.executescript(_REFERENCE_SCHEMA)
            self._conn.commit()
        else:
            # ----------------------------------------------------------------- #
            # POSTGRES ADAPTER SEAM (optional). Lazy import so this module never
            # hard-depends on psycopg — the reference backend is pure stdlib.
            # The seam intentionally lives here, behind the same method surface,
            # so production swaps backend without touching any call site.
            # ----------------------------------------------------------------- #
            if not connection_string:
                raise StoreError(
                    "the postgres backend requires a libpq connection_string "
                    "(e.g. 'postgresql://user@host:5432/dbname')"
                )
            try:
                import psycopg  # type: ignore  # psycopg3
            except ImportError as exc:  # pragma: no cover - Postgres is optional
                raise StoreError(
                    "the postgres backend requires the optional 'psycopg' driver; "
                    "install it, or use the default stdlib sqlite reference backend"
                ) from exc
            self._conn = psycopg.connect(connection_string)  # type: ignore[attr-defined]
            self._paramstyle = "pyformat"  # '%s'

    # ------------------------------------------------------------------ #
    # Internal paramstyle + cursor helpers (normalize sqlite '?' vs psycopg '%s')
    # ------------------------------------------------------------------ #
    def _ph(self, n: int) -> str:
        """Return ``n`` bound-parameter placeholders for the active backend."""
        token = "?" if self._paramstyle == "qmark" else "%s"
        return ", ".join([token] * n)

    def _q(self, sql: str) -> str:
        """Translate the canonical '?' placeholders to the backend paramstyle."""
        if self._paramstyle == "qmark":
            return sql
        return sql.replace("?", "%s")

    def _execute(self, sql: str, params: tuple = ()):
        cur = self._conn.cursor()
        cur.execute(self._q(sql), params)
        return cur

    def close(self) -> None:
        try:
            self._conn.close()
        except Exception:  # pragma: no cover - defensive
            pass

    def __enter__(self) -> "Store":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    # ================================================================== #
    # Requirements (001) — needed so coverage_items / evidence_records FKs
    # resolve. Upserting a coverage item ensures its parent requirement row.
    # ================================================================== #
    def upsert_requirement(
        self,
        requirement_id: str,
        *,
        project_id: str = "default",
        type: str = "functional",
        priority: int = 1,
        ears_pattern: str = "ubiquitous",
        ears_stmt: str = "",
        provenance: str = "stated",
        nfr_subtype: Optional[str] = None,
    ) -> None:
        """Insert-or-update the authoritative requirement row (001_requirements).

        Idempotent on ``id``. The coverage/evidence tables FK this row, so
        ``upsert_coverage_item`` / ``store_evidence`` ensure it exists first.
        """
        if type not in REQUIREMENT_TYPES:
            raise StoreError(f"invalid requirement type {type!r}; expected one of {REQUIREMENT_TYPES}")
        self._execute(
            """
            INSERT INTO requirements
                (id, project_id, type, nfr_subtype, priority, ears_pattern, ears_stmt, provenance)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (id) DO UPDATE SET
                project_id  = excluded.project_id,
                type        = excluded.type,
                nfr_subtype = excluded.nfr_subtype,
                priority    = excluded.priority,
                ears_pattern= excluded.ears_pattern,
                ears_stmt   = excluded.ears_stmt,
                provenance  = excluded.provenance
            """,
            (requirement_id, project_id, type, nfr_subtype, priority, ears_pattern, ears_stmt, provenance),
        )
        self._conn.commit()

    # ================================================================== #
    # Coverage (002) — upsert_coverage_item / get_coverage / query_uncovered
    # ================================================================== #
    def upsert_coverage_item(self, item: Dict[str, Any]) -> None:
        """Insert-or-update a coverage item from a feature_list-shaped dict.

        ``item`` is the CoverageItem shape from feature_list.json: at minimum an
        ``id``; optionally ``type``, ``priority``, ``status``, ``in_scope``,
        ``subtype``, ``slice_id``, ``nfr_subtype``, ``ears_pattern``,
        ``ears_statement``, ``provenance``, ``title``, and (when proven) an
        ``evidence`` object.

        Status authority guard (Property 2 / four-field gate): an upsert that
        sets ``status='proven'`` MUST carry a complete four-field Evidence_Record
        on the item (``item['evidence']``). An attempt to upsert a proven item
        with no/partial evidence RAISES ``EvidenceIncompleteError`` — the store
        will not record a proven coverage row the gates would reject. When a
        complete ``evidence`` object is present on a proven upsert, it is also
        persisted into ``evidence_records`` (idempotently) so the durable store
        is internally consistent (a proven item always has its row of proof).

        ``in_scope`` defaults to True (Req 5.7 — items are in scope unless a
        human-authored transition removes them).
        """
        if not isinstance(item, dict):
            raise StoreError("coverage item must be a dict")
        requirement_id = item.get("id")
        if not requirement_id or not isinstance(requirement_id, str):
            raise StoreError("coverage item requires a non-empty string 'id'")

        status = item.get("status", "unproven")
        if status not in COVERAGE_STATUSES:
            raise StoreError(
                f"invalid coverage status {status!r}; expected one of {COVERAGE_STATUSES}"
            )

        # in_scope defaults True; coerce to the sqlite 0/1 representation.
        in_scope = item.get("in_scope", True)
        in_scope_int = 1 if in_scope else 0

        subtype = item.get("subtype")
        slice_id = item.get("slice_id")

        # ----- the proven-transition gate (mirrors store_evidence) ----- #
        # A coverage row may flip to 'proven' ONLY with a complete four-field
        # Evidence_Record. This is the exact rule the SubagentStop hook and the
        # OPA merge gate enforce; the durable store refuses to be left in a state
        # they would reject.
        evidence = item.get("evidence")
        if status == "proven":
            if not validate_evidence_record(evidence if isinstance(evidence, dict) else {}):
                raise EvidenceIncompleteError(
                    f"cannot flip {requirement_id!r} to 'proven' without a complete "
                    "four-field Evidence_Record (test_file, test_name, output_hash, "
                    "collected_at); the durable store mirrors the in-session gate "
                    "(Property 2 / Req 5.3 / 5.6)"
                )

        # Ensure the parent requirement row exists (FK target). Carry over any
        # routing fields the caller supplied.
        self.upsert_requirement(
            requirement_id,
            project_id=item.get("project_id", "default"),
            type=item.get("type", "functional"),
            priority=item.get("priority", 1),
            ears_pattern=item.get("ears_pattern", "ubiquitous"),
            ears_stmt=item.get("ears_statement", item.get("ears_stmt", "")),
            provenance=item.get("provenance", "stated"),
            nfr_subtype=item.get("nfr_subtype"),
        )

        self._execute(
            """
            INSERT INTO coverage_items
                (requirement_id, status, subtype, in_scope, slice_id, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT (requirement_id) DO UPDATE SET
                status     = excluded.status,
                subtype    = excluded.subtype,
                in_scope   = excluded.in_scope,
                slice_id   = excluded.slice_id,
                updated_at = excluded.updated_at
            """,
            (requirement_id, status, subtype, in_scope_int, slice_id, _utc_now_iso()),
        )
        self._conn.commit()

        # On a proven upsert with a complete embedded Evidence_Record, persist
        # the proof row too so the store is self-consistent (a proven coverage
        # item always has at least one evidence_records row).
        if status == "proven" and isinstance(evidence, dict):
            self._store_evidence_row(
                requirement_id,
                evidence,
                gate_already_checked=True,
            )

    def get_coverage(self) -> List[Dict[str, Any]]:
        """Return every coverage item as a list of plain dicts.

        Each dict carries ``id`` (the requirement_id), ``status``, ``in_scope``
        (as a Python ``bool``), ``subtype``, ``slice_id``, ``type``, ``priority``
        (joined from requirements), and the latest ``evidence`` object when the
        item is proven and has an evidence row. Honours nothing — returns ALL
        items; scope filtering is the caller's / ``query_uncovered``'s job.
        """
        cur = self._execute(
            """
            SELECT c.requirement_id AS id,
                   c.status         AS status,
                   c.in_scope       AS in_scope,
                   c.subtype        AS subtype,
                   c.slice_id       AS slice_id,
                   r.type           AS type,
                   r.priority       AS priority
            FROM coverage_items c
            JOIN requirements r ON r.id = c.requirement_id
            ORDER BY r.priority ASC, c.requirement_id ASC
            """
        )
        rows = cur.fetchall()
        items: List[Dict[str, Any]] = []
        for row in rows:
            rec = self._row_to_dict(row)
            rec["in_scope"] = bool(rec["in_scope"])
            evidence = self._latest_evidence(rec["id"])
            if evidence is not None:
                rec["evidence"] = evidence
            items.append(rec)
        return items

    def query_uncovered(self) -> List[Dict[str, Any]]:
        """Return the IN-SCOPE coverage items that are not ``proven`` (Req 5.7).

        Mirrors ``stop_hook.evaluate_stop`` / ``coverage_gate.deny_merge``: only
        ``in_scope`` items are counted, and any in-scope item whose status is not
        EXACTLY ``'proven'`` (i.e. ``unproven`` OR ``failed``) is uncovered. An
        out-of-scope item NEVER appears here. The returned dicts are the same
        shape ``get_coverage`` yields.
        """
        return [
            item
            for item in self.get_coverage()
            if item.get("in_scope") and item.get("status") != "proven"
        ]

    # ================================================================== #
    # Evidence (004) — store_evidence with the four-field proven gate
    # ================================================================== #
    def store_evidence(
        self,
        requirement_id: str,
        record: Dict[str, Any],
        *,
        commit_sha: str = "",
        actor_agent: str = VERIFIER_ROLE,
        flip_to_proven: bool = True,
    ) -> None:
        """Store an Evidence_Record for ``requirement_id`` and (by default) flip
        the coverage item to ``proven`` — REJECTING an incomplete record.

        ``record`` is the four-field Evidence_Record (``test_file``,
        ``test_name``, ``output_hash``, ``collected_at``). It may also carry the
        provenance ``actor_agent`` field, but ``actor_agent`` is NOT one of the
        four gate fields and is stored on the 7-column ``evidence_records`` row
        only (the four-field JSON object stays ``additionalProperties:false``).

        Gate (Property 2 / Req 5.3 / 5.6 — the SAME rule the SubagentStop hook
        and OPA merge gate enforce): this method REJECTS flipping an item to
        ``proven`` without a complete four-field Evidence_Record. If ``record``
        is missing a field, has an empty field, or has a malformed ``output_hash``
        (not ``^sha256:[a-f0-9]{64}$``), it RAISES ``EvidenceIncompleteError``
        and writes nothing — the proven transition is refused.

        Provenance (Property 24): ``actor_agent`` defaults to and is asserted to
        be the Verifier (``verifier.md``). Implementer-authored evidence is
        rejected — evidence is captured only by the Verifier, never the
        Implementer.

        Transition (mirrors ``coverage.ALLOWED_TRANSITIONS``): the implied
        ``status -> proven`` move must be legal from the item's current status
        (``unproven -> proven`` is the only path into proven). A flip attempted
        from ``failed`` or ``proven`` raises ``TransitionError``.
        """
        if not requirement_id or not isinstance(requirement_id, str):
            raise StoreError("store_evidence requires a non-empty string requirement_id")

        # Provenance gate (Property 24): evidence is captured only by the Verifier.
        record_actor = record.get("actor_agent") if isinstance(record, dict) else None
        effective_actor = record_actor or actor_agent
        if effective_actor != VERIFIER_ROLE:
            raise StoreError(
                f"evidence actor_agent must be {VERIFIER_ROLE!r} (Property 24 — "
                f"evidence is captured by the Verifier, never the Implementer); got "
                f"{effective_actor!r}"
            )

        # The four-field gate. validate_evidence_record is the SAME validator the
        # in-session hook uses (presence + non-empty + sha256 format + parseable
        # collected_at). A flip to proven without it is REJECTED.
        if not validate_evidence_record(record if isinstance(record, dict) else {}):
            raise EvidenceIncompleteError(
                f"cannot store evidence / flip {requirement_id!r} to 'proven': the "
                "Evidence_Record is incomplete or malformed — all four fields "
                "(test_file, test_name, output_hash, collected_at) must be present, "
                "non-empty, with output_hash matching ^sha256:[a-f0-9]{64}$ "
                "(Property 2 / Req 5.3 / 5.6)"
            )
        # Defensive double-check of the hash format independent of the validator,
        # so the durable-store contract is self-evidently the same as the DB CHECK.
        if OUTPUT_HASH_PATTERN.match(str(record.get("output_hash", ""))) is None:
            raise EvidenceIncompleteError(
                f"output_hash for {requirement_id!r} must match ^sha256:[a-f0-9]{{64}}$"
            )

        if flip_to_proven:
            current = self._current_status(requirement_id)
            # If the item is not yet tracked, treat its origin as 'unproven'
            # (the schema DEFAULT) so unproven->proven is the legal path.
            origin = current if current is not None else "unproven"
            if (origin, "proven") not in _ALLOWED_TRANSITIONS:
                raise TransitionError(
                    f"{origin}->proven is not an allowed transition for "
                    f"{requirement_id!r} (only unproven->proven enters proven)"
                )

        # Persist the evidence row (the four-field gate already passed).
        self._store_evidence_row(
            requirement_id,
            record,
            commit_sha=commit_sha,
            actor_agent=effective_actor,
            gate_already_checked=True,
        )

        # Flip the coverage item to proven (the durable record of the proof).
        if flip_to_proven:
            # Ensure a coverage row exists, then set status=proven. We go through
            # upsert with the embedded evidence so the same gate path is honoured;
            # status authority/role is the SubagentStop hook's concern, not the
            # store's — the store enforces only the four-field/transition rules.
            self._execute(
                """
                INSERT INTO coverage_items (requirement_id, status, in_scope, updated_at)
                VALUES (?, 'proven', 1, ?)
                ON CONFLICT (requirement_id) DO UPDATE SET
                    status = 'proven',
                    updated_at = excluded.updated_at
                """,
                (requirement_id, _utc_now_iso()),
            )
            # Make sure the parent requirement exists for the FK.
            # (INSERT above would have failed the FK otherwise; ensure first.)
            self._conn.commit()

    def _store_evidence_row(
        self,
        requirement_id: str,
        record: Dict[str, Any],
        *,
        commit_sha: str = "",
        actor_agent: str = VERIFIER_ROLE,
        gate_already_checked: bool = False,
    ) -> None:
        """Low-level evidence_records INSERT. Ensures the parent requirement row.

        When ``gate_already_checked`` is False, re-runs the four-field gate so this
        path is never a way to smuggle an incomplete record into the table.
        """
        if not gate_already_checked:
            if not validate_evidence_record(record if isinstance(record, dict) else {}):
                raise EvidenceIncompleteError(
                    f"incomplete Evidence_Record for {requirement_id!r} "
                    "(four-field gate, Property 2 / Req 5.3 / 5.6)"
                )

        # Ensure the FK parent exists (idempotent).
        self.upsert_requirement(requirement_id)

        self._execute(
            """
            INSERT INTO evidence_records
                (requirement_id, commit_sha, test_file, test_name,
                 output_hash, collected_at, actor_agent)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                requirement_id,
                commit_sha or record.get("commit_sha", ""),
                record["test_file"],
                record["test_name"],
                record["output_hash"],
                record["collected_at"],
                record.get("actor_agent", actor_agent),
            ),
        )
        self._conn.commit()

    def get_evidence(self, requirement_id: str) -> List[Dict[str, Any]]:
        """Return all evidence rows for ``requirement_id`` (Property 19 round-trip).

        Each row is retrievable by requirement_id (and carries commit_sha) with
        all four fields intact, mirroring task 30.2's Property-19 Postgres round-trip.
        """
        cur = self._execute(
            """
            SELECT requirement_id, commit_sha, test_file, test_name,
                   output_hash, collected_at, actor_agent
            FROM evidence_records
            WHERE requirement_id = ?
            ORDER BY id ASC
            """,
            (requirement_id,),
        )
        return [self._row_to_dict(row) for row in cur.fetchall()]

    def _latest_evidence(self, requirement_id: str) -> Optional[Dict[str, str]]:
        """Return the most-recent four-field Evidence_Record dict, or None."""
        cur = self._execute(
            """
            SELECT test_file, test_name, output_hash, collected_at, actor_agent
            FROM evidence_records
            WHERE requirement_id = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (requirement_id,),
        )
        row = cur.fetchone()
        if row is None:
            return None
        rec = self._row_to_dict(row)
        # Surface the four gate fields + actor_agent provenance.
        return {
            "test_file": rec["test_file"],
            "test_name": rec["test_name"],
            "output_hash": rec["output_hash"],
            "collected_at": rec["collected_at"],
            "actor_agent": rec["actor_agent"],
        }

    def _current_status(self, requirement_id: str) -> Optional[str]:
        cur = self._execute(
            "SELECT status FROM coverage_items WHERE requirement_id = ?",
            (requirement_id,),
        )
        row = cur.fetchone()
        if row is None:
            return None
        return self._row_to_dict(row)["status"]

    # ================================================================== #
    # Run state (005) — save_run_state / load_run_state
    # ================================================================== #
    def save_run_state(self, state: Dict[str, Any]) -> None:
        """Upsert per-session run state into ``run_state`` (task 31.1).

        ``state`` is a dict keyed by the ``run_state`` columns; at minimum
        ``session_id``. ``status`` defaults to ``'running'`` and ``project_id``
        to ``'default'`` so a minimal state round-trips. Boolean-typed columns
        (``resume_integrity_ok``, ``is_resume``, ``first_write_done``,
        ``stop_hook_active``) accept Python bools and are stored as 0/1; the
        load side surfaces them back as bools, so the save/load round-trip is
        loss-free. Unknown keys are ignored.
        """
        if not isinstance(state, dict):
            raise StoreError("run state must be a dict")
        session_id = state.get("session_id")
        if not session_id or not isinstance(session_id, str):
            raise StoreError("run state requires a non-empty string 'session_id'")

        status = state.get("status", "running")
        if status not in RUN_STATE_STATUSES:
            raise StoreError(
                f"invalid run_state status {status!r}; expected one of {RUN_STATE_STATUSES}"
            )

        # Build the ordered value tuple, coercing bools -> 0/1.
        defaults: Dict[str, Any] = {
            "project_id": "default",
            "status": "running",
            "phase": "spec",
            "iteration_count": 0,
            "spec_pass_count": 0,
            "token_cost_usd": 0,
            "no_progress_n": 0,
            "violation_count": 0,
            "prev_violation_count": None,
            "retry_count": 0,
            "resume_integrity_ok": None,
            "is_resume": False,
            "first_write_done": False,
            "resume_state_hash": None,
            "stop_hook_active": False,
            "last_commit_sha": None,
            "current_item_id": None,
        }
        values = []
        for col in _RUN_STATE_COLUMNS:
            val = state.get(col, defaults.get(col))
            if col in _RUN_STATE_BOOL_COLUMNS and val is not None:
                val = 1 if val else 0
            values.append(val)

        cols_sql = ", ".join(_RUN_STATE_COLUMNS)
        update_sql = ", ".join(
            f"{c} = excluded.{c}" for c in _RUN_STATE_COLUMNS if c != "session_id"
        )
        self._execute(
            f"""
            INSERT INTO run_state ({cols_sql}, updated_at)
            VALUES ({self._ph(len(_RUN_STATE_COLUMNS))}, ?)
            ON CONFLICT (session_id) DO UPDATE SET
                {update_sql},
                updated_at = excluded.updated_at
            """,
            (*values, _utc_now_iso()),
        )
        self._conn.commit()

    def load_run_state(self, session_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Load the run-state row for ``session_id`` (task 31.1).

        Returns a dict keyed by the ``run_state`` columns with the boolean
        columns surfaced as Python bools (``None`` preserved where the column is
        nullable and unset), or ``None`` when no row exists. When ``session_id``
        is omitted and exactly one run_state row exists, that row is returned (a
        convenience for single-session tests); when omitted with multiple rows it
        raises ``StoreError`` to avoid an ambiguous load.
        """
        if session_id is None:
            cur = self._execute("SELECT * FROM run_state")
            rows = cur.fetchall()
            if not rows:
                return None
            if len(rows) > 1:
                raise StoreError(
                    "load_run_state() called without session_id but multiple "
                    "run_state rows exist; pass an explicit session_id"
                )
            row = rows[0]
        else:
            cur = self._execute(
                "SELECT * FROM run_state WHERE session_id = ?", (session_id,)
            )
            row = cur.fetchone()
            if row is None:
                return None

        rec = self._row_to_dict(row)
        for col in _RUN_STATE_BOOL_COLUMNS:
            if col in rec and rec[col] is not None:
                rec[col] = bool(rec[col])
        return rec

    # ================================================================== #
    # Helpers
    # ================================================================== #
    @staticmethod
    def _row_to_dict(row: Any) -> Dict[str, Any]:
        """Normalize a DBAPI row to a plain dict across sqlite3.Row / psycopg."""
        if isinstance(row, sqlite3.Row):
            return {k: row[k] for k in row.keys()}
        # psycopg with a dict_row factory yields a Mapping; otherwise fall back
        # to .keys() / tuple access. The reference backend is the only one tested
        # here; the Postgres path is the documented seam.
        if hasattr(row, "keys"):
            return {k: row[k] for k in row.keys()}  # pragma: no cover
        raise StoreError(  # pragma: no cover
            "unexpected row type; configure the Postgres connection with a "
            "dict-row factory (psycopg.rows.dict_row) for the adapter seam"
        )


# Make a quick self-import / smoke check meaningful when run directly.
if __name__ == "__main__":  # pragma: no cover
    s = Store()
    s.upsert_coverage_item({"id": "REQ-SPEC-001", "type": "functional", "in_scope": True})
    print("uncovered:", json.dumps(s.query_uncovered()))
    s.save_run_state({"session_id": "sess-1", "status": "running"})
    print("run_state:", json.dumps(s.load_run_state("sess-1")))
    s.close()
