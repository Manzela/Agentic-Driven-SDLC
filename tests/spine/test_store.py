"""Independent verifier tests for tools/store.py (slice: store).

Written by the INDEPENDENT VERIFIER, not the implementer. The implementer's
own tests are not imported, read, or trusted here — this file re-derives the
contract straight from the task and asserts it against the live Store object.

REQ-STORE-001..003  (Durable Storage; tasks 30, 31 — plane requirement REQ-STORE)

Contract under test (four points, each its own test):

  1. ROUND-TRIP — an in-memory Store round-trips coverage items + run_state:
     what you upsert/save is what you read back (Property 19's spirit, run
     state included; bool columns survive as bools).

  2. PROVEN FLIP — store_evidence with a COMPLETE four-field Evidence_Record
     flips the coverage item's status to 'proven' AND the record is
     retrievable afterwards (round-trip of the proof, Property 19).

  3. INCOMPLETE REJECTED — store_evidence with an INCOMPLETE record RAISES and
     does NOT flip: the item stays not-proven and no evidence row is written
     (Property 2 / Req 5.3 / 5.6 — the four-field proven gate).

  4. SCOPE — query_uncovered returns ONLY in_scope, non-proven items; an
     out-of-scope item never appears, a proven in-scope item never appears
     (Req 5.7).

store.py uses a flat internal import (``from evidence_collector import ...``),
so tools/ must be on sys.path — exactly the convention test_feature_list_init.py
already uses. We mirror it rather than inventing a new one.
"""

import os
import sys

import pytest

# <repo>/tests/spine/test_store.py -> repo root is two levels up.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_TOOLS = os.path.join(_REPO_ROOT, "tools")
# Put tools/ on the path so store.py's flat `from evidence_collector import ...`
# resolves (the import convention the module was written against).
if _TOOLS not in sys.path:
    sys.path.insert(0, _TOOLS)

from store import (  # noqa: E402  (path injected above)
    EvidenceIncompleteError,
    Store,
)


# --------------------------------------------------------------------------- #
# Fixtures / builders — independently derived, no implementer helpers reused.
# --------------------------------------------------------------------------- #
# A well-formed output_hash: literal "sha256:" + exactly 64 lowercase hex chars.
_GOOD_HASH = "sha256:" + ("a" * 64)


def _complete_record(tag: str = "t1") -> dict:
    """A complete, contract-valid four-field Evidence_Record."""
    return {
        "test_file": f"tests/spine/test_{tag}.py",
        "test_name": f"test_{tag}_behaviour",
        "output_hash": _GOOD_HASH,
        "collected_at": "2026-06-16T00:00:00+00:00",
    }


@pytest.fixture()
def store():
    """A fresh in-memory (reference backend) Store per test."""
    s = Store()  # ":memory:" sqlite reference backend
    try:
        yield s
    finally:
        s.close()


def _status_of(store, item_id):
    """Read the live status of a coverage item straight from get_coverage()."""
    for item in store.get_coverage():
        if item["id"] == item_id:
            return item["status"]
    return None


# --------------------------------------------------------------------------- #
# 1. ROUND-TRIP — coverage items + run_state
# --------------------------------------------------------------------------- #
def test_coverage_item_round_trips(store):
    """Upsert a coverage item; read the same id/status/in_scope/slice back."""
    store.upsert_coverage_item(
        {"id": "REQ-A-001", "status": "unproven", "in_scope": True, "slice_id": "store"}
    )

    items = store.get_coverage()
    ids = {i["id"] for i in items}
    assert "REQ-A-001" in ids, "upserted coverage item is not retrievable"

    rec = next(i for i in items if i["id"] == "REQ-A-001")
    assert rec["status"] == "unproven"
    assert rec["in_scope"] is True, "in_scope must round-trip as a Python bool True"
    assert rec["slice_id"] == "store"


def test_run_state_round_trips(store):
    """save_run_state -> load_run_state is loss-free, bools survive as bools."""
    saved = {
        "session_id": "sess-rt-1",
        "project_id": "proj-store",
        "status": "running",
        "iteration_count": 3,
        "is_resume": True,
        "first_write_done": True,
        "stop_hook_active": False,
        "last_commit_sha": "deadbeef",
    }
    store.save_run_state(saved)

    loaded = store.load_run_state("sess-rt-1")
    assert loaded is not None, "saved run_state row must be retrievable"
    assert loaded["session_id"] == "sess-rt-1"
    assert loaded["project_id"] == "proj-store"
    assert loaded["status"] == "running"
    assert loaded["iteration_count"] == 3
    # Boolean columns must survive the 0/1 storage round-trip AS bools.
    assert loaded["is_resume"] is True
    assert loaded["first_write_done"] is True
    assert loaded["stop_hook_active"] is False
    assert loaded["last_commit_sha"] == "deadbeef"
    # An unknown session yields None, not a stale row.
    assert store.load_run_state("no-such-session") is None


# --------------------------------------------------------------------------- #
# 2. PROVEN FLIP — complete record flips to proven AND is retrievable
# --------------------------------------------------------------------------- #
def test_store_evidence_complete_flips_to_proven_and_is_retrievable(store):
    """A complete Evidence_Record flips the item to 'proven' and round-trips."""
    store.upsert_coverage_item({"id": "REQ-B-001", "status": "unproven", "in_scope": True})
    assert _status_of(store, "REQ-B-001") == "unproven", "precondition: not yet proven"

    record = _complete_record("b1")
    store.store_evidence("REQ-B-001", record)  # actor defaults to verifier

    # The flip happened.
    assert _status_of(store, "REQ-B-001") == "proven", "complete record must flip to proven"

    # The proof is retrievable with all four fields intact (Property 19).
    rows = store.get_evidence("REQ-B-001")
    assert len(rows) == 1, "exactly one evidence row should be stored"
    row = rows[0]
    assert row["requirement_id"] == "REQ-B-001"
    assert row["test_file"] == record["test_file"]
    assert row["test_name"] == record["test_name"]
    assert row["output_hash"] == record["output_hash"]
    assert row["collected_at"] == record["collected_at"]


# --------------------------------------------------------------------------- #
# 3. INCOMPLETE REJECTED — raises, and does NOT flip / does NOT write
# --------------------------------------------------------------------------- #
def test_store_evidence_incomplete_raises_and_does_not_flip(store):
    """An incomplete record RAISES; the item stays not-proven, no row written."""
    store.upsert_coverage_item({"id": "REQ-C-001", "status": "unproven", "in_scope": True})

    incomplete = _complete_record("c1")
    del incomplete["output_hash"]  # drop a required field -> incomplete record

    with pytest.raises(EvidenceIncompleteError):
        store.store_evidence("REQ-C-001", incomplete)

    # No flip: status is unchanged.
    assert _status_of(store, "REQ-C-001") == "unproven", "incomplete record must NOT flip to proven"
    # No evidence row leaked into the table.
    assert store.get_evidence("REQ-C-001") == [], "incomplete record must not be persisted"


def test_store_evidence_malformed_hash_raises_and_does_not_flip(store):
    """A present-but-malformed output_hash is also rejected (format gate)."""
    store.upsert_coverage_item({"id": "REQ-C-002", "status": "unproven", "in_scope": True})

    bad = _complete_record("c2")
    bad["output_hash"] = "sha256:NOTHEX"  # wrong format -> rejected

    with pytest.raises(EvidenceIncompleteError):
        store.store_evidence("REQ-C-002", bad)

    assert _status_of(store, "REQ-C-002") == "unproven"
    assert store.get_evidence("REQ-C-002") == []


# --------------------------------------------------------------------------- #
# 4. SCOPE — query_uncovered: only in_scope, non-proven (ignores out-of-scope)
# --------------------------------------------------------------------------- #
def test_query_uncovered_only_in_scope_non_proven(store):
    """query_uncovered returns in-scope unproven/failed; never proven/out-of-scope."""
    # in-scope, unproven  -> SHOULD appear
    store.upsert_coverage_item({"id": "REQ-D-UNPROVEN", "status": "unproven", "in_scope": True})
    # in-scope, failed    -> SHOULD appear (failed != proven)
    store.upsert_coverage_item({"id": "REQ-D-FAILED", "status": "failed", "in_scope": True})
    # in-scope, proven    -> SHOULD NOT appear
    store.upsert_coverage_item(
        {"id": "REQ-D-PROVEN", "status": "proven", "in_scope": True,
         "evidence": _complete_record("d-proven")}
    )
    # OUT-OF-SCOPE, unproven -> MUST be ignored even though it's not proven
    store.upsert_coverage_item({"id": "REQ-D-OOS", "status": "unproven", "in_scope": False})

    uncovered_ids = {i["id"] for i in store.query_uncovered()}

    assert "REQ-D-UNPROVEN" in uncovered_ids, "in-scope unproven must be uncovered"
    assert "REQ-D-FAILED" in uncovered_ids, "in-scope failed (non-proven) must be uncovered"
    assert "REQ-D-PROVEN" not in uncovered_ids, "proven item must never be uncovered"
    assert "REQ-D-OOS" not in uncovered_ids, "out-of-scope item must be ignored (Req 5.7)"

    # And every returned item genuinely satisfies the predicate.
    for item in store.query_uncovered():
        assert item["in_scope"] is True
        assert item["status"] != "proven"
