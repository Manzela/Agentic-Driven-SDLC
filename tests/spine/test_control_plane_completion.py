"""Phase-0 control-plane completion: hook config, coverage helpers, OPA input."""
import json
import pathlib
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]


def test_settings_all_six_hooks_command_type():
    settings = json.loads((ROOT / ".claude" / "settings.json").read_text())
    hooks = settings["hooks"]
    for evt in ("PreToolUse", "PostToolUse", "Stop", "SubagentStop", "PreCompact", "SessionStart"):
        assert evt in hooks, f"missing hook: {evt}"
        for matcher in hooks[evt]:
            for h in matcher["hooks"]:
                assert h["type"] == "command", f"{evt} must be command-type (fail-closed)"
                assert "url" not in h and "http" not in json.dumps(h), f"{evt} must not be http/mcp"


def test_four_agents_exist_and_verifier_is_readonly():
    for a in ("verifier", "implementer", "initializer", "research"):
        assert (ROOT / ".claude" / "agents" / f"{a}.md").is_file()
    vt = (ROOT / ".claude" / "agents" / "verifier.md").read_text().lower()
    # Merge-resolution (2026-06-16): main's canonical verifier.md wins over the
    # website-tailored copy; assert its read-only-on-src invariant by main's wording.
    assert "read-only" in vt and ("never write" in vt or "no write" in vt)


def test_coverage_transitions_and_authority():
    from tools.coverage import (assert_transition, assert_field_authority,
                                TransitionError, AuthorityError, is_complete)
    assert_transition("unproven", "proven")  # ok
    with pytest.raises(TransitionError):
        assert_transition("failed", "proven")
    assert_field_authority(field="status", actor_agent="verifier.md", human_signed=False)
    with pytest.raises(AuthorityError):
        assert_field_authority(field="status", actor_agent="implementer.md", human_signed=False)
    with pytest.raises(AuthorityError):
        assert_field_authority(field="in_scope", actor_agent="verifier.md", human_signed=False)
    assert is_complete({"items": [{"in_scope": True, "status": "proven"}]}) is True
    assert is_complete({"items": [{"in_scope": True, "status": "unproven"}]}) is False
    assert is_complete({"items": []}) is False  # empty model is INIT, not COMPLETE


def test_opa_input_flags_unproven_and_missing_evidence(tmp_path):
    from tools.opa_input import build_opa_input
    p = tmp_path / "fl.json"
    p.write_text(json.dumps({"items": [
        {"id": "A-B-001", "in_scope": True, "status": "unproven", "evidence": None},
        {"id": "A-B-002", "in_scope": True, "status": "proven", "evidence": None},
        {"id": "A-B-003", "in_scope": True, "status": "proven", "evidence": {"x": 1}},
        {"id": "A-B-004", "in_scope": False, "status": "unproven", "evidence": None},
    ]}))
    out = build_opa_input(p)
    assert out["unproven_in_scope"] == ["A-B-001"]
    assert out["missing_evidence"] == ["A-B-002"]


def test_precompact_and_session_start_roundtrip():
    import importlib.util
    def load(name):
        sp = importlib.util.spec_from_file_location(name, ROOT / ".claude" / "hooks" / f"{name}.py")
        m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m
    pc = load("pre_compact_hook"); ss = load("session_start_hook")
    fl = {"items": [{"in_scope": True, "status": "proven"}, {"in_scope": True, "status": "unproven"}]}
    # Merge-resolution (2026-06-16): main's canonical hook API — pre_compact(state)
    # returns a non-blocking checkpoint payload; session_start(feature_list, progress,
    # git_status) returns the in-scope proven/unproven counts.
    cp = pc.pre_compact({"feature_list": fl})
    assert cp["ok"] is True and isinstance(cp["checkpointed"], list)
    summary = ss.session_start(fl, None, None)
    assert summary["proven_count"] == 1 and summary["unproven_count"] == 1
