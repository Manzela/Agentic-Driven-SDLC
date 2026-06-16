"""End-to-end spine integration test (Phase-3, tasks 16 + 17).

Spec: .kiro/specs/spec-to-evidence-control — REQ-GATE-002 / REQ-LOOP-005 /
REQ-VERIFY / Property 2 / Property 22.

This is a SMOKE + INTEGRATION test that wires the REAL spine components end to
end — no mocks, no re-implementations. It imports the actual production modules
from the repo:

  * tools/feature_list_init.py   — init_feature_list / write_feature_list
  * tools/coverage_gate.py       — deny_merge (the OPA-equivalent merge gate)
  * .claude/hooks/stop_hook.py   — evaluate_stop (the Stop completion gate)
  * tools/evidence_collector.py  — collect / validate_evidence_record

and drives one in-scope functional coverage item through its full lifecycle,
asserting the two independent gates (merge gate + Stop gate) move in lock-step
with the item's status. It proves the spine works TOGETHER, not just unit-wise:

  1. feature_list_init seeds a coverage model with ONE in-scope functional item
     whose status is 'unproven'.
  2. coverage_gate.deny_merge -> DENIED (an unproven in-scope item blocks merge).
  3. stop_hook.evaluate_stop -> BLOCK (not all in-scope items proven).
  4. evidence_collector.collect produces a complete four-field Evidence_Record;
     we attach it and flip the item to 'proven'.
  5. coverage_gate.deny_merge -> NOT denied (proven + complete evidence).
  6. stop_hook.evaluate_stop, no HANDOFF trigger -> ALLOW / COMPLETE.
  7. a cap-reached run_state -> evaluate_stop ALLOW / HANDOFF (never block) — the
     load-bearing infinite-block fix: at cap the in-scope item may remain
     unproven yet termination is ALLOWED.

The whole feature_list object is round-tripped through write_feature_list at the
proven stage so the gates are exercised against a SCHEMA-VALIDATED, on-disk
document, not just an in-memory dict.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

# ── Resolve the repo root and put it on sys.path so `tools.*` imports resolve
#    regardless of the cwd pytest is invoked from. The repo root is two levels
#    up from this file (tests/integration/test_spine_e2e.py).
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# ── Import the REAL tool modules as a package (rootdir is on sys.path). ───────
from tools.coverage_gate import deny_merge  # noqa: E402
from tools.evidence_collector import collect, validate_evidence_record  # noqa: E402
from tools.feature_list_init import (  # noqa: E402
    init_feature_list,
    validate_against_schema,
    write_feature_list,
)

# ── Import the Stop hook by file path. It lives under .claude/hooks/, which is
#    not an importable package, so we load it explicitly (same technique the
#    standalone stop-hook verifier uses).
_HOOK_PATH = _REPO_ROOT / ".claude" / "hooks" / "stop_hook.py"
_spec = importlib.util.spec_from_file_location("stop_hook_e2e", _HOOK_PATH)
assert _spec is not None and _spec.loader is not None, (
    f"could not load stop_hook from {_HOOK_PATH}"
)
stop_hook = importlib.util.module_from_spec(_spec)
sys.modules["stop_hook_e2e"] = stop_hook
_spec.loader.exec_module(stop_hook)
evaluate_stop = stop_hook.evaluate_stop


# ── Fixture builders (owned by this test — independent of the components). ────

# A single in-scope, functional coverage item. The id matches the schema's
# ^[A-Z]+-[A-Z]+-[0-9]{3}$ pattern and the item carries exactly the
# CoverageItem-required fields so it (and the whole feature_list) validates.
_ITEM_ID = "REQ-SPINE-001"


def _functional_item() -> dict:
    """A raw in-scope functional item; normalization defaults status->unproven."""
    return {
        "id": _ITEM_ID,
        "type": "functional",
        "priority": 1,
        "title": "Spine end-to-end smoke item",
        "acceptance_criteria": [
            "feature_list -> merge gate -> Stop gate -> evidence -> proven path holds",
        ],
        # status / in_scope intentionally omitted so the initializer's
        # normalization seeds status='unproven' and in_scope=True.
    }


def _run_state(**overrides: object) -> dict:
    """A clean run_state with NO HANDOFF trigger active.

    iteration_count below the cap, no budget breach, no no-progress streak, and
    zero outstanding spec violations — so evaluate_stop's decision is driven
    purely by the coverage model, not by a HANDOFF/blocking-violation shortcut.
    """
    base: dict = {
        "iteration_count": 0,
        "budget_exceeded": False,
        "no_progress_n": 0,
        "violation_count": 0,
    }
    base.update(overrides)
    return base


def _build_feature_list() -> dict:
    """Seed the coverage model via the REAL initializer (one in-scope item)."""
    fl = init_feature_list(
        [_functional_item()],
        product_class="agentic-sdlc-control-plane",
        checklist_ref={
            "path": "checklists/agentic-sdlc.md",
            "version": "1.0.0",
            "sha": "0" * 40,
        },
    )
    # Sanity: the initializer must seed status='unproven' and in_scope=True.
    item = fl["items"][0]
    assert item["status"] == "unproven", item
    assert item["in_scope"] is True, item
    # And the seeded envelope must itself validate against the file schema.
    validate_against_schema(fl)
    return fl


# ── The end-to-end spine flow ─────────────────────────────────────────────────


def test_spine_end_to_end(tmp_path: Path) -> None:
    """Drive one in-scope functional item through the full spine lifecycle.

    Each numbered block corresponds to one spine stage; the assertions tie the
    two independent gates (merge gate + Stop gate) to the item's status so a
    regression in any single component surfaces here as a wiring failure.
    """
    run_state = _run_state()

    # ── (1) INIT: feature_list with one in-scope functional item, unproven. ──
    feature_list = _build_feature_list()
    assert len(feature_list["items"]) == 1
    assert feature_list["items"][0]["status"] == "unproven"

    # ── (2) Merge gate over the UNPROVEN model -> DENIED. ────────────────────
    merge_before = deny_merge(feature_list)
    assert merge_before["deny"] is True, merge_before
    # The deny reason must name our in-scope unproven item, not a fail-closed
    # malformed-input shortcut — i.e. the gate genuinely evaluated the item.
    assert any(_ITEM_ID in r and "not 'proven'" in r for r in merge_before["reasons"]), (
        merge_before
    )

    # ── (3) Stop gate over the UNPROVEN model, no HANDOFF -> BLOCK. ───────────
    stop_before = evaluate_stop(run_state, feature_list)
    assert stop_before["decision"] == "block", stop_before
    assert stop_before["terminal"] is None, stop_before
    assert _ITEM_ID in stop_before["reason"], stop_before

    # ── (4) Collect a complete Evidence_Record and flip item -> proven. ──────
    #    The artifact text is hashed by the collector; we do not fabricate the
    #    hash — collect() computes the sha256 and the timezone-aware timestamp.
    evidence = collect(
        test_file="tests/integration/test_spine_e2e.py",
        test_name="test_spine_end_to_end",
        output="PASS: spine functional item behavioral proof artifact",
    )
    # The collected record must satisfy the SHARED validator the in-session
    # SubagentStop gate uses — proving collect() and the gate agree.
    assert validate_evidence_record(evidence) is True, evidence

    item = feature_list["items"][0]
    item["evidence"] = evidence
    item["status"] = "proven"

    # The now-proven model must still be schema-valid (status=proven REQUIRES an
    # evidence object via the schema allOf). Round-trip it through the REAL
    # writer so the gates below run against an on-disk, schema-validated doc.
    fl_path = tmp_path / "feature_list.json"
    written = write_feature_list(feature_list, str(fl_path))
    with open(written, "r", encoding="utf-8") as fh:
        on_disk = json.load(fh)
    assert on_disk["items"][0]["status"] == "proven"
    assert validate_evidence_record(on_disk["items"][0]["evidence"]) is True

    # ── (5) Merge gate over the PROVEN model -> NOT denied. ──────────────────
    merge_after = deny_merge(on_disk)
    assert merge_after["deny"] is False, merge_after
    assert merge_after["reasons"] == [], merge_after

    # ── (6) Stop gate over the PROVEN model, no HANDOFF -> ALLOW / COMPLETE. ──
    stop_after = evaluate_stop(run_state, on_disk)
    assert stop_after["decision"] == "allow", stop_after
    assert stop_after["terminal"] == "COMPLETE", stop_after

    # ── (7) Cap-reached run_state -> ALLOW / HANDOFF, NEVER block. ───────────
    #    The infinite-block fix: at the iteration cap, even an UNPROVEN model
    #    must route to HANDOFF (allow), not block the agent past its cap.
    capped_state = _run_state(iteration_count=stop_hook.MAX_TURNS_PER_SLICE)
    # Use the original unproven model to prove HANDOFF wins regardless of
    # coverage status (the in-scope item is still unproven there).
    unproven_model = _build_feature_list()
    handoff = evaluate_stop(capped_state, unproven_model)
    assert handoff["decision"] == "allow", handoff
    assert handoff["terminal"] == "HANDOFF", handoff
    assert handoff["decision"] != "block", handoff


# ── Additional spine-smoke guards (task 16) — each gate's directional sense. ──


def test_merge_gate_denies_empty_coverage_model() -> None:
    """An empty (zero in-scope items) model is a valid INIT, never a valid
    merge state -> the merge gate must DENY it rather than vacuously pass."""
    empty = init_feature_list()  # items == []
    decision = deny_merge(empty)
    assert decision["deny"] is True, decision


def test_stop_gate_blocks_empty_coverage_model() -> None:
    """Symmetrically, the Stop gate must BLOCK an empty model (run discovery
    first) rather than read it as COMPLETE."""
    empty = init_feature_list()  # items == []
    decision = evaluate_stop(_run_state(), empty)
    assert decision["decision"] == "block", decision
    assert decision["terminal"] is None, decision


def test_handoff_precedes_completion_block_with_unproven_item() -> None:
    """Cap/HANDOFF is evaluated BEFORE the unproven-items blocking gate: with an
    unproven in-scope item AND the iteration cap reached, the decision is
    ALLOW/HANDOFF, not BLOCK (the load-bearing ordering of evaluate_stop)."""
    fl = _build_feature_list()  # one unproven in-scope item
    capped = _run_state(iteration_count=stop_hook.MAX_TURNS_PER_SLICE + 5)
    decision = evaluate_stop(capped, fl)
    assert decision["decision"] == "allow", decision
    assert decision["terminal"] == "HANDOFF", decision


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
