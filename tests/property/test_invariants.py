"""test_invariants.py — Hypothesis property-based invariants over the REAL
built control-plane components (Phase-3 property_suite, task 39 / Properties 1-32).

This module imports the ACTUAL implementation modules from the worktree — it does
NOT re-implement their logic. It asserts the load-bearing invariants of the
spec-to-evidence control plane over Hypothesis-generated inputs, so the gates are
proven not just on hand-picked cases but across the generated input space:

  * P5 / P22 — ``coverage_gate.deny_merge`` denies a merge IFF some in-scope item
    is not exactly proven-with-complete-evidence (and out-of-scope items never
    contribute a deny; an empty in-scope model denies).
  * stop    — ``stop_hook.evaluate_stop`` returns terminal COMPLETE only when all
    in-scope items are proven and NO handoff trigger is active; and routes to
    terminal HANDOFF with decision=allow (NEVER block) whenever a cap / budget /
    no-progress trigger fires.
  * P28     — ``audit_log`` hash chains always verify untampered, and verification
    FAILS the moment any single entry field is mutated.
  * P2      — ``evidence_collector.validate_evidence_record`` accepts every
    complete record and rejects any record missing/emptying any required field.

Determinism: there is NO use of ``datetime.now`` / ``random`` / wall-clock outside
Hypothesis's own strategies. Every generated timestamp / hash / id is produced by a
strategy (or a fixed literal), so a given Hypothesis seed reproduces the exact run.

Import contract: the spec instructs ``sys.path.insert`` for ``tools/`` and
``.claude/hooks/``. We resolve those two directories relative to this file (so the
suite is location-independent) and import the real modules by their bare names:
``coverage_gate``, ``evidence_collector``, ``audit_log`` (from ``tools/``) and
``stop_hook`` (from ``.claude/hooks/``).
"""

from __future__ import annotations

import copy
import dataclasses
import pathlib
import sys

from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st

# ── Real-component imports (sys.path.insert per the task contract) ───────────
# Resolve the worktree root from this file: tests/property/test_invariants.py
# → parents[2] is the repo root. Insert tools/ and .claude/hooks/ onto sys.path
# so the bare-name imports below bind to the ACTUAL built modules.
_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
_TOOLS_DIR = _REPO_ROOT / "tools"
_HOOKS_DIR = _REPO_ROOT / ".claude" / "hooks"
for _p in (str(_TOOLS_DIR), str(_HOOKS_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import audit_log  # noqa: E402  (real tools/audit_log.py)
import coverage_gate  # noqa: E402  (real tools/coverage_gate.py)
import evidence_collector  # noqa: E402  (real tools/evidence_collector.py)
import stop_hook  # noqa: E402  (real .claude/hooks/stop_hook.py)

# Pull the constants the gates are parameterized by straight from the real
# modules, so these tests track the implementation rather than hard-coding a
# value that could silently drift.
EVIDENCE_FIELDS = evidence_collector._REQUIRED_FIELDS  # 4-field record contract
MAX_TURNS = stop_hook.MAX_TURNS_PER_SLICE
N_PROGRESS = stop_hook.N_PROGRESS_WINDOW

# A shared profile: no example deadline (some chains/strategies are a little
# heavier), and tolerate the function-scoped-fixture health check noise (we use
# none, but keep the suite robust under different pytest plugin configs).
_SETTINGS = settings(
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)


# ── Shared strategies ────────────────────────────────────────────────────────

# A well-formed, non-empty hex output_hash matching evidence_collector's anchored
# ``^sha256:[a-f0-9]{64}$`` pattern. Built from generated hex so it varies across
# examples but is always format-valid.
_hex64 = st.text(alphabet="0123456789abcdef", min_size=64, max_size=64)
valid_output_hash = _hex64.map(lambda h: "sha256:" + h)

# A parseable ISO-8601 timestamp. We generate from a small fixed set of valid
# RFC-3339 strings (datetime.fromisoformat must accept them); no wall clock.
valid_collected_at = st.sampled_from(
    [
        "2026-06-16T00:00:00+00:00",
        "2026-01-02T03:04:05+00:00",
        "2025-12-31T23:59:59+00:00",
        "2026-06-16T12:30:00Z",
        "2026-06-16T12:30:00.123456+00:00",
    ]
)

# Non-empty free text for the string evidence fields (test_file / test_name).
# bounded so generation stays cheap; ``.filter`` drops whitespace-only strings
# since the validator treats those as empty.
nonempty_text = st.text(min_size=1, max_size=24).filter(lambda s: s.strip() != "")

# A complete, valid four-field Evidence_Record.
complete_evidence = st.fixed_dictionaries(
    {
        "test_file": nonempty_text,
        "test_name": nonempty_text,
        "output_hash": valid_output_hash,
        "collected_at": valid_collected_at,
        # Actor-separation (Phase A, commit d98a3b8): a proven item's evidence must
        # name DISTINCT implementer/verifier sessions, else deny_merge denies it as a
        # self-grade. Distinct ids keep "all proven + complete evidence => mergeable".
        "implementer_session_id": st.just("sess-impl"),
        "verifier_session_id": st.just("sess-veri"),
    }
)

# Item ids — short, may collide across a list (the gates key/sort by id but do
# not require uniqueness), and explicitly include the empty string so the
# ``<no-id>`` / ``str("")`` fallbacks are exercised.
item_ids = st.one_of(
    st.just(""),
    st.text(alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ-_0123456789", min_size=1, max_size=8),
)

# Item statuses — the full set the gate distinguishes plus odd values, so
# "not exactly proven" is exercised across many shapes.
item_status = st.sampled_from(["proven", "unproven", "failed", "pending", "", "PROVEN"])


@st.composite
def feature_items(draw: st.DrawFn) -> dict:
    """Draw one feature_list item with arbitrary scope/status/evidence.

    The four axes that the coverage/stop gates branch on are all generated
    independently so the cross-product (in_scope × status × evidence-complete ×
    evidence-present) is explored:

      * ``in_scope``        — bool (out-of-scope items must never affect a deny).
      * ``status``          — from ``item_status`` (only exact "proven" passes).
      * evidence presence   — sometimes the ``evidence`` key is absent entirely.
      * evidence completeness — when present, either a complete record or one
        with a single required field blanked/dropped (an incomplete record).
    """
    item: dict = {
        "id": draw(item_ids),
        "in_scope": draw(st.booleans()),
        "status": draw(item_status),
    }
    has_evidence = draw(st.booleans())
    if has_evidence:
        ev = draw(complete_evidence)
        # With some probability, corrupt exactly one field to make the record
        # incomplete — exercising the proven-but-partial deny path. The corruption
        # set now includes NON-STRING values (None/False/[]/number): the schema is
        # type:string,minLength:1, so a non-string field is invalid evidence, and the
        # twins must agree on it (red-team: the old strategy only ever blanked/dropped
        # a field, so the rego⇔python non-string split was never generated).
        if draw(st.booleans()):
            field = draw(st.sampled_from(list(EVIDENCE_FIELDS)))
            ev[field] = draw(st.sampled_from(["", None, False, [], 0, 42]))
            if ev[field] is None and draw(st.booleans()):
                ev.pop(field, None)  # also exercise the fully-absent case
        item["evidence"] = ev
    return item


feature_list_strategy = st.fixed_dictionaries(
    {"items": st.lists(feature_items(), min_size=0, max_size=6)}
)


def _is_proven_with_complete_evidence(item: dict) -> bool:
    """Oracle (independent of coverage_gate) for 'exactly proven + complete 4-field
    Evidence_Record'. Used to predict the gate's deny decision from first
    principles rather than by calling the function under test.
    """
    if item.get("status") != "proven":
        return False
    ev = item.get("evidence")
    if not isinstance(ev, dict):
        return False
    for field in EVIDENCE_FIELDS:
        val = ev.get(field)
        # Each field MUST be a non-empty STRING (schema type:string,minLength:1); a
        # non-string value is invalid evidence -> incomplete (matches both gate twins).
        if not isinstance(val, str) or val.strip() == "":
            return False
    return True


# ── P5 / P22 — coverage_gate.deny_merge ──────────────────────────────────────


@_SETTINGS
@given(feature_list=feature_list_strategy)
def test_deny_merge_iff_some_in_scope_item_not_proven_with_evidence(feature_list: dict) -> None:
    """P5/P22: ``deny_merge`` denies IFF the set of in-scope items is non-empty
    AND some in-scope item is not exactly proven-with-complete-evidence.

    The expected decision is computed by an INDEPENDENT oracle
    (``_is_proven_with_complete_evidence`` + the empty-in-scope rule), then
    compared to the gate's actual ``deny`` flag. This is a true biconditional:
    we assert both directions on every generated model.
    """
    result = coverage_gate.deny_merge(feature_list)
    assert isinstance(result, dict)
    assert isinstance(result["deny"], bool)

    in_scope = [i for i in feature_list["items"] if i.get("in_scope")]
    if not in_scope:
        # Empty in-scope model is a valid INIT state but never COMPLETE/merge →
        # the gate must deny (it must not vacuously pass).
        expected_deny = True
    else:
        expected_deny = any(
            not _is_proven_with_complete_evidence(i) for i in in_scope
        )

    assert result["deny"] is expected_deny
    # A deny must always carry at least one reason; an allow must carry none.
    assert bool(result["reasons"]) is expected_deny


@_SETTINGS
@given(
    in_scope_items=st.lists(
        st.fixed_dictionaries(
            {
                "id": item_ids,
                "in_scope": st.just(True),
                "status": st.just("proven"),
                "evidence": complete_evidence,
            }
        ),
        min_size=1,
        max_size=5,
    ),
    out_of_scope_items=st.lists(feature_items(), min_size=0, max_size=4),
)
def test_deny_merge_allows_all_proven_and_ignores_out_of_scope(
    in_scope_items: list, out_of_scope_items: list
) -> None:
    """P5/P22 (allow direction + scope filter): when EVERY in-scope item is
    proven-with-complete-evidence, the merge is allowed regardless of any number
    of arbitrary OUT-OF-SCOPE items mixed in. Out-of-scope items never deny.
    """
    # Force every "out_of_scope" item out of scope so it can only contribute a
    # deny via a (forbidden) scope leak.
    for it in out_of_scope_items:
        it["in_scope"] = False

    feature_list = {"items": [*in_scope_items, *out_of_scope_items]}
    result = coverage_gate.deny_merge(feature_list)

    assert result["deny"] is False
    assert result["reasons"] == []


# ── P2 — WIRING integration-evidence gate (Task 9) ───────────────────────────

wiring_evidence_kinds = st.sampled_from(
    ["unit", "integration", "behavioral", "perf", "a11y", None]
)


@_SETTINGS
@given(kind=wiring_evidence_kinds, item_type=st.sampled_from(["WIRING", "functional", "NFR"]))
def test_deny_merge_wiring_requires_integration_evidence_kind(kind, item_type) -> None:
    """P2 (Req 8.3): a proven in-scope item carrying a COMPLETE four-field
    Evidence_Record with DISTINCT sessions is denied for the evidence_kind reason IFF
    it is a WIRING item whose ``evidence_kind`` is not 'integration'. A unit/behavioral/
    etc. record cannot prove a WIRING obligation; non-WIRING items are unaffected by
    evidence_kind (backward compat). The expected decision is computed independently."""
    ev = {
        "test_file": "t", "test_name": "n",
        "output_hash": "sha256:" + "a" * 64, "collected_at": "2026-06-16T00:00:00+00:00",
        "implementer_session_id": "sess-impl", "verifier_session_id": "sess-veri",
    }
    if kind is not None:
        ev["evidence_kind"] = kind
    item = {"id": "REQ-X-001", "type": item_type, "in_scope": True,
            "status": "proven", "evidence": ev}
    result = coverage_gate.deny_merge({"items": [item]})

    kind_denied = any("evidence_kind" in r for r in result["reasons"])
    should_deny_for_kind = item_type == "WIRING" and kind != "integration"
    assert kind_denied == should_deny_for_kind, (
        f"type={item_type} kind={kind!r}: kind-deny={kind_denied}, "
        f"expected={should_deny_for_kind}; reasons={result['reasons']}"
    )
    # A WIRING item WITH integration evidence (otherwise complete) is fully mergeable;
    # a non-WIRING item with any kind is likewise not denied on these inputs.
    if (item_type == "WIRING" and kind == "integration") or item_type != "WIRING":
        assert result["deny"] is False, f"unexpected deny: {result['reasons']}"


# ── stop — stop_hook.evaluate_stop ───────────────────────────────────────────

# run_state strategies. Each axis the decision branches on is generated.
_iteration_count = st.integers(min_value=0, max_value=MAX_TURNS + 5)
_no_progress_n = st.integers(min_value=0, max_value=N_PROGRESS + 2)
_violation_count = st.integers(min_value=-1, max_value=3)


def _handoff_trigger_active(run_state: dict) -> bool:
    """Oracle for 'a HANDOFF trigger is active' — mirrors the three precedence
    triggers evaluate_stop checks first (iteration cap, budget, no-progress)."""
    if int(run_state.get("iteration_count", 0) or 0) >= MAX_TURNS:
        return True
    if run_state.get("budget_exceeded"):
        return True
    if int(run_state.get("no_progress_n", 0) or 0) >= N_PROGRESS:
        return True
    return False


run_state_strategy = st.fixed_dictionaries(
    {
        "iteration_count": _iteration_count,
        "budget_exceeded": st.booleans(),
        "no_progress_n": _no_progress_n,
        "violation_count": _violation_count,
    }
)


@st.composite
def stop_feature_list(draw: st.DrawFn) -> dict:
    """A feature_list for the Stop gate: items with in_scope + a status only
    (evidence is irrelevant to evaluate_stop's completion gate, which keys on
    status == 'proven')."""
    items = draw(
        st.lists(
            st.fixed_dictionaries(
                {
                    "id": item_ids,
                    "in_scope": st.booleans(),
                    "status": item_status,
                }
            ),
            min_size=0,
            max_size=6,
        )
    )
    return {"items": items}


@_SETTINGS
@given(run_state=run_state_strategy, feature_list=stop_feature_list())
def test_evaluate_stop_handoff_always_allows_never_blocks(
    run_state: dict, feature_list: dict
) -> None:
    """stop: whenever ANY HANDOFF trigger (iteration cap / budget / no-progress)
    is active, evaluate_stop ALLOWS termination with terminal=HANDOFF and NEVER
    blocks — even though in-scope items are expected to remain unproven (the
    infinite-block-defect fix). This is asserted across the full generated
    run_state × feature_list space.
    """
    decision = stop_hook.evaluate_stop(run_state, feature_list)

    if _handoff_trigger_active(run_state):
        assert decision["decision"] == "allow"
        assert decision["terminal"] == "HANDOFF"


@_SETTINGS
@given(run_state=run_state_strategy, feature_list=stop_feature_list())
def test_evaluate_stop_complete_only_when_all_proven_and_no_handoff(
    run_state: dict, feature_list: dict
) -> None:
    """stop: evaluate_stop returns terminal COMPLETE IFF (no HANDOFF trigger is
    active) AND (violation_count == 0) AND (there is at least one in-scope item)
    AND (every in-scope item has status exactly 'proven').

    Both directions:
      * COMPLETE  ⇒ the full proven/no-violation/no-handoff predicate holds.
      * predicate ⇒ the decision is exactly allow+COMPLETE.
    """
    decision = stop_hook.evaluate_stop(run_state, feature_list)

    in_scope = [i for i in feature_list["items"] if i.get("in_scope")]
    handoff = _handoff_trigger_active(run_state)
    violations_clean = int(run_state.get("violation_count", 0) or 0) == 0
    all_proven = bool(in_scope) and all(
        i.get("status") == "proven" for i in in_scope
    )
    expect_complete = (not handoff) and violations_clean and all_proven

    if decision.get("terminal") == "COMPLETE":
        # COMPLETE is necessarily an allow, and the full predicate must hold.
        assert decision["decision"] == "allow"
        assert not handoff
        assert violations_clean
        assert all_proven

    if expect_complete:
        # The predicate holding must yield exactly allow + COMPLETE.
        assert decision["decision"] == "allow"
        assert decision["terminal"] == "COMPLETE"

    # COMPLETE happens IFF the predicate holds.
    assert (decision.get("terminal") == "COMPLETE") is expect_complete


# ── P28 — audit_log hash-chain tamper detection ──────────────────────────────

# An append's positional argument tuple: (event, tool, decision, reason,
# requirement_id, actor_agent). event + actor_agent are non-empty (the producer
# raises on empty); tool/reason/requirement_id are nullable.
_append_args = st.tuples(
    nonempty_text,                                  # event (non-null)
    st.one_of(st.none(), nonempty_text),            # tool (nullable)
    st.sampled_from(["allow", "block"]),            # decision (DDL CHECK)
    st.one_of(st.none(), nonempty_text),            # reason (nullable)
    st.one_of(st.none(), nonempty_text),            # requirement_id (nullable)
    nonempty_text,                                  # actor_agent (non-null)
)


@_SETTINGS
@given(rows=st.lists(_append_args, min_size=0, max_size=6))
def test_audit_chain_verifies_untampered(rows: list) -> None:
    """P28: a freshly produced chain of N appended entries ALWAYS verifies True,
    via both the instance and the module-level verifier. seq is 1-based monotonic
    and each prev_hash links to the prior entry_hash (genesis sentinel first).
    """
    log = audit_log.AuditLog()
    for (event, tool, decision, reason, req_id, actor) in rows:
        log.append(event, tool, decision, reason, req_id, actor)

    assert log.verify_chain() is True
    assert audit_log.verify_chain(log.entries) is True

    entries = log.entries
    assert [e.seq for e in entries] == list(range(1, len(entries) + 1))
    prev = audit_log.GENESIS_PREV_HASH
    for e in entries:
        assert e.prev_hash == prev
        prev = e.entry_hash


# Hashed/canonical fields whose mutation MUST break the chain. prev_hash and
# entry_hash are the chaining fields; seq + the eight canonical columns are
# hashed. (tool_name/reason/requirement_id are nullable but still hashed.)
_MUTABLE_FIELDS = st.sampled_from(
    [
        "seq",
        "event_name",
        "tool_name",
        "decision",
        "reason",
        "requirement_id",
        "actor_agent",
        "created_at",
        "prev_hash",
        "entry_hash",
    ]
)


@_SETTINGS
@given(
    rows=st.lists(_append_args, min_size=1, max_size=6),
    target_index=st.integers(min_value=0, max_value=5),
    field=_MUTABLE_FIELDS,
    new_str=st.text(min_size=1, max_size=12),
)
def test_audit_chain_detects_any_single_mutation(
    rows: list, target_index: int, field: str, new_str: str
) -> None:
    """P28: mutating ANY single field of ANY entry breaks verify_chain (it returns
    False). AuditEntry is a frozen dataclass, so we rebuild the entries list with
    one field replaced (the same effect as an in-place row tamper) and re-verify.
    """
    log = audit_log.AuditLog()
    for (event, tool, decision, reason, req_id, actor) in rows:
        log.append(event, tool, decision, reason, req_id, actor)

    entries = log.entries
    idx = target_index % len(entries)
    original = entries[idx]
    old_value = getattr(original, field)

    # Compute a genuinely different value for the chosen field so the mutation is
    # real (a no-op replacement would leave the chain valid).
    if field == "seq":
        new_value = old_value + 1
    elif field in ("decision",):
        # Flip allow<->block (any string != current; both are hashed columns).
        new_value = "block" if old_value == "allow" else "allow"
    else:
        # String / nullable-string field: pick a value distinct from current.
        new_value = new_str if new_str != old_value else new_str + "X"

    assume(new_value != old_value)

    tampered_entry = dataclasses.replace(original, **{field: new_value})
    tampered = list(entries)
    tampered[idx] = tampered_entry

    assert audit_log.verify_chain(tampered) is False


# ── P2 — evidence_collector.validate_evidence_record ─────────────────────────


@_SETTINGS
@given(record=complete_evidence)
def test_validate_evidence_accepts_complete_records(record: dict) -> None:
    """P2: every complete, well-formed four-field Evidence_Record is accepted."""
    assert evidence_collector.validate_evidence_record(record) is True


@_SETTINGS
@given(
    record=complete_evidence,
    drop_field=st.sampled_from(list(EVIDENCE_FIELDS)),
    mode=st.sampled_from(["missing", "none", "empty", "whitespace"]),
)
def test_validate_evidence_rejects_missing_or_empty_field(
    record: dict, drop_field: str, mode: str
) -> None:
    """P2: removing, nulling, blanking, or whitespace-only-ing ANY single required
    field makes the record invalid. Starts from a known-complete record and
    corrupts exactly one field, so rejection is attributable to that field alone.
    """
    rec = copy.deepcopy(record)
    if mode == "missing":
        rec.pop(drop_field, None)
    elif mode == "none":
        rec[drop_field] = None
    elif mode == "empty":
        rec[drop_field] = ""
    else:  # whitespace
        rec[drop_field] = "   "

    assert evidence_collector.validate_evidence_record(rec) is False


@_SETTINGS
@given(
    record=complete_evidence,
    bad_hash=st.one_of(
        st.text(min_size=1, max_size=20),                      # arbitrary junk
        _hex64.map(lambda h: h),                                # 64 hex, NO prefix
        _hex64.map(lambda h: "sha256:" + h.upper()),           # UPPERCASE hex
        _hex64.map(lambda h: "sha256:" + h[:-1]),              # 63 hex (too short)
        _hex64.map(lambda h: "sha256:" + h + "a"),             # 65 hex (too long)
    ),
)
def test_validate_evidence_rejects_malformed_output_hash(
    record: dict, bad_hash: str
) -> None:
    """P2: a present-but-malformed ``output_hash`` (missing prefix, uppercase hex,
    wrong length, or arbitrary junk) is rejected — not just absent fields. Guard
    against the bad_hash happening to be valid (the generated valid case is
    excluded so the assertion is sound).
    """
    assume(evidence_collector.OUTPUT_HASH_PATTERN.match(bad_hash) is None)
    rec = copy.deepcopy(record)
    rec["output_hash"] = bad_hash
    assert evidence_collector.validate_evidence_record(rec) is False
