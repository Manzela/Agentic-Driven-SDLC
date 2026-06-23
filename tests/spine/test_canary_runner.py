# tests/spine/test_canary_runner.py
#
# Regression coverage for tools/run_spine_canary.py — the spine's GATE. Because
# this file's entire purpose is to be the gate, its own evidence-collection and
# orchestration logic is regression-tested here over fixture fire-sinks /
# transcripts / run_state — not just the three pure assertion helpers.
#
# Three bands:
#   (1) the FIVE pure assertion helpers (no live model), incl. the two added
#       live-only assertions assert_positive_path / assert_governance_terminal;
#   (2) the load-bearing PLUMBING — _normalize/_jaccard/_row_text, the JSONL/JSON
#       loaders, _fire_evidence;
#   (3) the ORCHESTRATION — _negative_controls + its _record block/non-block
#       logic (proving the gates BITE), and main()'s SKIP-vs-FAIL flow — both
#       exercised with _run_hook monkeypatched so the band is hermetic.
import importlib.util
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]


def _load():
    spec = importlib.util.spec_from_file_location(
        "run_spine_canary", ROOT / "tools/run_spine_canary.py"
    )
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# ── Band 1: the three original pure assertion helpers ───────────────────────

def test_reinjection_detects_near_duplicates():
    c = _load()
    rows = [{"role": "user", "content": "continue: 5 violations remain"},
            {"role": "user", "content": "continue: 4 violations remain"}]  # near-dup
    with pytest.raises(AssertionError):
        c.assert_no_reinjection(rows, jaccard=0.9)


def test_reinjection_allows_distinct_steering():
    c = _load()
    rows = [{"role": "user", "content": "implement the parser for slice A"},
            {"role": "user", "content": "now write the schema migration for B"}]
    c.assert_no_reinjection(rows, jaccard=0.9)  # must NOT raise


def test_all_hooks_fired_requires_full_set():
    c = _load()
    fires = [{"hook_event": e} for e in ["SessionStart", "PreToolUse", "Stop"]]
    with pytest.raises(AssertionError):
        c.assert_all_hooks_fired(
            fires,
            {"SessionStart", "PreToolUse", "PostToolUse",
             "SubagentStop", "Stop", "PreCompact"},
        )


def test_all_hooks_fired_passes_on_full_set():
    c = _load()
    req = {"SessionStart", "PreToolUse", "PostToolUse",
           "SubagentStop", "Stop", "PreCompact"}
    fires = [{"hook_event": e} for e in req]
    c.assert_all_hooks_fired(fires, req)  # must NOT raise


def test_ralph_absent_flags_stop_hook_sh():
    c = _load()
    with pytest.raises(AssertionError):
        c.assert_ralph_absent(
            [{"hook_event": "Stop", "command_path": "/x/ralph-loop/stop-hook.sh"}])


def test_ralph_absent_passes_on_spine_only_paths():
    c = _load()
    c.assert_ralph_absent(
        [{"hook_event": "Stop", "command_path": "/repo/.claude/hooks/stop_hook.py"}])


# ── Band 1b: the two added live-only assertions ─────────────────────────────

def _verifier_fire(vsid="vses", isid="ises"):
    return {
        "hook_event": "SubagentStop",
        "agent_type": "verifier",
        "evidence": {
            "actor_agent": "verifier",
            "verifier_session_id": vsid,
            "implementer_session_id": isid,
        },
    }


def _fl(status="proven", item_id="CANARY-001", in_scope=True):
    return {"items": [{"id": item_id, "in_scope": in_scope, "status": status}]}


def test_positive_path_passes_with_distinct_verifier_fire():
    c = _load()
    c.assert_positive_path([_verifier_fire()], _fl(), slice_id="CANARY-001")


def test_positive_path_blocks_when_proven_without_any_verifier_fire():
    c = _load()
    with pytest.raises(AssertionError):
        c.assert_positive_path([], _fl(), slice_id="CANARY-001")


def test_positive_path_blocks_on_same_session_self_grade():
    c = _load()
    fire = _verifier_fire(vsid="same", isid="same")  # not distinct → self-grade
    with pytest.raises(AssertionError):
        c.assert_positive_path([fire], _fl(), slice_id="CANARY-001")


def test_positive_path_blocks_when_proving_fire_is_not_a_verifier():
    c = _load()
    impostor = {
        "hook_event": "SubagentStop", "agent_type": "implementer",
        "evidence": {"verifier_session_id": "v", "implementer_session_id": "i"},
    }
    with pytest.raises(AssertionError):
        c.assert_positive_path([impostor], _fl(), slice_id="CANARY-001")


def test_positive_path_blocks_when_slice_never_reached_proven():
    c = _load()
    with pytest.raises(AssertionError):
        # the slice we asked about is still unproven → never legitimately closed
        c.assert_positive_path([_verifier_fire()], _fl(status="unproven"),
                               slice_id="CANARY-001")


def test_positive_path_reads_evidence_from_nested_tool_input():
    c = _load()
    nested = {
        "hook_event": "SubagentStop", "agent_type": "verifier",
        "tool_input": {"evidence": {"verifier_session_id": "v",
                                    "implementer_session_id": "i"}},
    }
    c.assert_positive_path([nested], _fl(), slice_id="CANARY-001")


def _rs(status="COMPLETE", **extra):
    base = {"status": status, "iteration_count": 3}
    base.update(extra)
    return base


def test_governance_terminal_passes_on_complete():
    c = _load()
    c.assert_governance_terminal(_rs("COMPLETE"), max_turns=25)


def test_governance_terminal_passes_on_handoff_lowercase():
    c = _load()
    c.assert_governance_terminal(_rs("handoff"), max_turns=25)


def test_governance_terminal_blocks_on_running_status():
    c = _load()
    with pytest.raises(AssertionError):
        c.assert_governance_terminal(_rs("running"), max_turns=25)


def test_governance_terminal_blocks_on_empty_run_state():
    c = _load()
    with pytest.raises(AssertionError):
        c.assert_governance_terminal({}, max_turns=25)


def test_governance_terminal_blocks_on_watchdog_kill():
    c = _load()
    with pytest.raises(AssertionError):
        c.assert_governance_terminal(_rs("COMPLETE", watchdog_kill=True), max_turns=25)


def test_governance_terminal_blocks_on_manual_stop():
    c = _load()
    with pytest.raises(AssertionError):
        c.assert_governance_terminal(_rs("HANDOFF", manual_stop=True), max_turns=25)


def test_governance_terminal_blocks_on_wrong_terminated_by():
    c = _load()
    with pytest.raises(AssertionError):
        c.assert_governance_terminal(
            _rs("COMPLETE", terminated_by="watchdog"), max_turns=25)


def test_governance_terminal_passes_with_governance_terminated_by():
    c = _load()
    c.assert_governance_terminal(
        _rs("COMPLETE", terminated_by="governance_stop_hook"), max_turns=25)


def test_governance_terminal_blocks_on_max_turns_overrun():
    c = _load()
    with pytest.raises(AssertionError):
        c.assert_governance_terminal(_rs("COMPLETE", iteration_count=25), max_turns=25)


# ── Band 2: load-bearing plumbing (normalize / jaccard / row_text / loaders) ─

def test_normalize_strips_timestamps_and_digits():
    c = _load()
    a = c._normalize("Continue: 5 violations remain at 2026-06-22T00:00:00Z")
    b = c._normalize("Continue: 41 violations remain at 2026-06-21T13:14:15Z")
    assert a == b  # only the digits/timestamp differed → identical normalized form


def test_jaccard_identity_and_disjoint():
    c = _load()
    assert c._jaccard({"a", "b"}, {"a", "b"}) == 1.0
    assert c._jaccard({"a"}, {"b"}) == 0.0
    assert c._jaccard(set(), set()) == 1.0  # both empty → defined as identical


def test_row_text_handles_string_list_and_nested_message():
    c = _load()
    assert c._row_text({"content": "hello"}) == "hello"
    assert "x" in c._row_text({"content": [{"text": "x"}, {"text": "y"}]})
    assert c._row_text({"message": {"content": "deep"}}) == "deep"


def test_load_fire_rows_skips_blank_and_malformed(tmp_path):
    c = _load()
    sink = tmp_path / "fire.jsonl"
    sink.write_text(
        '{"hook_event":"Stop"}\n\nnot json\n{"hook_event":"PreToolUse"}\n',
        encoding="utf-8",
    )
    rows = c._load_fire_rows(sink)
    assert [r["hook_event"] for r in rows] == ["Stop", "PreToolUse"]


def test_load_fire_rows_missing_file_is_empty(tmp_path):
    c = _load()
    assert c._load_fire_rows(tmp_path / "nope.jsonl") == []


def test_load_json_object_blank_and_non_object(tmp_path):
    c = _load()
    good = tmp_path / "rs.json"
    good.write_text('{"status":"COMPLETE"}', encoding="utf-8")
    assert c._load_json(good) == {"status": "COMPLETE"}
    assert c._load_json(tmp_path / "missing.json") == {}
    arr = tmp_path / "arr.json"
    arr.write_text("[1,2,3]", encoding="utf-8")  # not an object
    assert c._load_json(arr) == {}


def test_load_transcript_rows_parses_jsonl(tmp_path):
    c = _load()
    t = tmp_path / "t.jsonl"
    t.write_text('{"role":"user","content":"a"}\n{"role":"assistant"}\n',
                 encoding="utf-8")
    rows = c._load_transcript_rows(t)
    assert len(rows) == 2 and rows[0]["content"] == "a"


def test_fire_evidence_inline_nested_and_absent():
    c = _load()
    assert c._fire_evidence({"evidence": {"k": 1}}) == {"k": 1}
    assert c._fire_evidence({"tool_input": {"evidence": {"k": 2}}}) == {"k": 2}
    assert c._fire_evidence({"hook_event": "Stop"}) == {}
    assert c._fire_evidence("not a dict") == {}


# ── Band 3: orchestration — _record / _negative_controls bite, hermetic ─────

def test_negative_controls_all_bite_when_hooks_block(monkeypatch, tmp_path):
    """Every negative control must report ok=True when its hook BLOCKS (rc=2)."""
    c = _load()
    # Force every hook subprocess to BLOCK (the expected, healthy state).
    monkeypatch.setattr(c, "_run_hook",
                        lambda *a, **k: (2, "", "forced violation blocked"))
    controls = c._negative_controls(tmp_path)
    assert controls, "expected a non-empty control set"
    assert all(ok for _, ok, _ in controls), \
        f"a control failed to register as biting: {controls}"
    # All six forced-violation controls must be present.
    assert len(controls) == 6


def test_negative_control_fails_when_a_gate_stops_biting(monkeypatch, tmp_path):
    """If a hook ALLOWS (rc=0) where a block is required, that control fails.

    This is the regression the suite must catch: a hook-path typo or env leak
    that makes a negative control stop biting would otherwise pass silently.
    """
    c = _load()
    calls = {"n": 0}

    def fake_run(*a, **k):
        calls["n"] += 1
        # First control LEAKS through (allow); the rest still block.
        return (0, "", "") if calls["n"] == 1 else (2, "", "blocked")

    monkeypatch.setattr(c, "_run_hook", fake_run)
    controls = c._negative_controls(tmp_path)
    oks = [ok for _, ok, _ in controls]
    assert oks[0] is False        # the leaked gate is flagged
    assert all(oks[1:])           # the rest still bite


def test_record_detail_carries_rc_and_reason(monkeypatch, tmp_path):
    c = _load()
    monkeypatch.setattr(c, "_run_hook",
                        lambda *a, **k: (2, "", "  protected path X  "))
    controls = c._negative_controls(tmp_path)
    # detail strings surface the rc and a trimmed reason snippet.
    assert any("rc=2" in detail and "protected path" in detail
               for _, _, detail in controls)


# ── Band 3b: main()'s SKIP-vs-FAIL flow (default no-live mode), hermetic ─────

def test_main_skips_live_assertions_without_live_flag(monkeypatch, capsys):
    """Default mode: negative controls run; the 5 live assertions are SKIP.

    main() must return 0 when every gate bites and nothing FAILs, and the five
    live-only assertions must be reported SKIP (not silently dropped).
    """
    c = _load()
    monkeypatch.setattr(c, "_run_hook",
                        lambda *a, **k: (2, "", "blocked as expected"))
    rc = c.main([])  # no --live
    out = capsys.readouterr().out
    assert rc == 0
    assert "SKIP" in out
    # All five live-only assertion names are present and skipped.
    for name in ("all six hooks fired", "ralph absent", "no re-injection",
                 "positive path (verifier-proven)", "governance terminal"):
        assert name in out


def test_main_returns_nonzero_when_a_negative_control_leaks(monkeypatch, capsys):
    """If any gate stops biting, main()'s gate must go red (return 1)."""
    c = _load()
    monkeypatch.setattr(c, "_run_hook",
                        lambda *a, **k: (0, "", ""))  # nothing blocks → all leak
    rc = c.main([])
    out = capsys.readouterr().out
    assert rc == 1
    assert "FAIL" in out
    assert "NOT ready" in out
