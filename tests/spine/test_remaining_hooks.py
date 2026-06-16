"""Independent verifier test for S11-hooks (REQ-VERIFY-004 / REQ-STATE-002, tasks 18,25).

Written by the VERIFIER, NOT the implementer. Loads each hook's pure core directly
from .claude/hooks and asserts the load-bearing contract behaviors.

post_tool_use (REQ-VERIFY-004, task 18):
  * Returns decision "non_block" and NEVER raises / NEVER blocks, even when every
    injected runner produces failing / HIGH / CRITICAL findings.
  * Collects the runner findings into a non-empty feedback list.

pre_compact (REQ-STATE-002, task 25):
  * Returns ok=True and a NON-EMPTY checkpointed list that INCLUDES
    feature_list.json when that artifact exists.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

# ── Load the hook modules directly from .claude/hooks (not on sys.path) ──────

_HOOKS_DIR = Path(__file__).resolve().parents[2] / ".claude" / "hooks"
_POST_PATH = _HOOKS_DIR / "post_tool_use_hook.py"
_PRE_PATH = _HOOKS_DIR / "pre_compact_hook.py"


def _load(path: Path, name: str):
    assert path.exists(), f"hook missing at {path}"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


post_hook = _load(_POST_PATH, "post_tool_use_hook_under_test")
pre_hook = _load(_PRE_PATH, "pre_compact_hook_under_test")


# ── post_tool_use: decision is always "non_block" ────────────────────────────

def _edit_event(path: str = "/repo/src/foo.py") -> dict:
    return {"tool_name": "Write", "tool_input": {"file_path": path}}


def test_post_tool_use_returns_non_block_decision_basic():
    result = post_hook.post_tool_use(_edit_event(), runners={})
    assert result["decision"] == "non_block", result


def test_post_tool_use_never_blocks_with_failing_high_critical_findings():
    """Even when every runner returns HIGH/CRITICAL/error findings, the
    decision MUST stay "non_block" — the PostToolUse never-blocks invariant."""
    runners = {
        "lint": lambda paths: [
            {"severity": "error", "rule": "E999", "message": "syntax error", "path": paths[0]},
        ],
        "sast": lambda paths: [
            {"severity": "critical", "check_id": "py.sql-injection", "message": "SQLi", "path": paths[0]},
            {"severity": "high", "check_id": "py.hardcoded-secret", "message": "secret", "path": paths[0]},
        ],
        "wiring": lambda paths: [
            {"severity": "high", "rule": "unwired-handler", "message": "dangling wire", "path": paths[0]},
        ],
    }
    result = post_hook.post_tool_use(_edit_event(), runners=runners)
    assert result["decision"] == "non_block", result
    # The findings are surfaced as advisory feedback, not a block.
    assert isinstance(result["feedback"], list)
    severities = {f["severity"] for f in result["feedback"]}
    assert {"critical", "high", "error"} <= severities, severities


def test_post_tool_use_collects_feedback_items():
    """Findings from each runner are collected into the feedback list."""
    runners = {
        "lint": lambda paths: [{"severity": "warning", "message": "lint-1"}],
        "sast": lambda paths: [{"severity": "high", "message": "sast-1"}],
        "wiring": lambda paths: [{"severity": "info", "message": "wire-1"}],
    }
    result = post_hook.post_tool_use(_edit_event(), runners=runners)
    assert result["decision"] == "non_block"
    msgs = {f["message"] for f in result["feedback"]}
    assert {"lint-1", "sast-1", "wire-1"} <= msgs, result
    assert len(result["feedback"]) == 3, result
    sources = {f["source"] for f in result["feedback"]}
    assert sources == {"lint", "sast", "wiring"}, sources


def test_post_tool_use_does_not_raise_when_runner_throws():
    """A runner that raises degrades to advisory feedback — never propagates."""
    def boom(paths):
        raise RuntimeError("runner exploded")

    runners = {"lint": boom, "sast": boom, "wiring": boom}
    # Must not raise.
    result = post_hook.post_tool_use(_edit_event(), runners=runners)
    assert result["decision"] == "non_block", result
    # The raised errors are captured as advisory (info) feedback, not re-raised.
    assert result["feedback"], result
    assert all(f["severity"] == "info" for f in result["feedback"]), result
    assert any("runner exploded" in f["message"] for f in result["feedback"]), result


def test_post_tool_use_non_block_on_malformed_event():
    """A garbage / empty event must still yield a well-formed non_block."""
    for bad in (None, {}, {"tool_name": None}, {"tool_input": "not-a-dict"}):
        result = post_hook.post_tool_use(bad, runners={})
        assert result["decision"] == "non_block", (bad, result)
        assert isinstance(result["feedback"], list), (bad, result)


def test_post_tool_use_no_paths_yields_empty_feedback_but_non_block():
    """A non-edit tool carries no changed paths → no findings, still non_block."""
    event = {"tool_name": "Read", "tool_input": {"file_path": "/repo/x.py"}}
    result = post_hook.post_tool_use(event, runners={"lint": lambda p: [{"message": "x"}]})
    assert result["decision"] == "non_block", result
    assert result["feedback"] == [], result


def test_post_tool_use_main_shell_exits_nonblocking():
    """The stdin shell must NEVER return exit code 2 (the blocking channel)."""
    code = post_hook.main.__code__
    # main() returns 1 (non-blocking feedback channel), never 2.
    rc = _run_main_with_stdin(post_hook, json.dumps(_edit_event()))
    assert rc != 2, f"PostToolUse main exited with blocking code {rc}"
    assert rc == 1, rc
    assert code is not None


def _run_main_with_stdin(module, payload: str) -> int:
    import io
    import sys
    old = sys.stdin
    sys.stdin = io.StringIO(payload)
    try:
        return module.main()
    finally:
        sys.stdin = old


# ── pre_compact: ok=True + non-empty checkpoint including feature_list.json ───

def test_pre_compact_ok_true_and_checkpoints_feature_list(tmp_path):
    # Build a minimal but realistic durable-state tree in a temp worktree.
    (tmp_path / "feature_list.json").write_text(
        json.dumps({"items": [{"id": "A", "status": "unproven"}]}), encoding="utf-8"
    )
    (tmp_path / "claude-progress.txt").write_text("step 3 of 9", encoding="utf-8")
    ev = tmp_path / "evidence"
    ev.mkdir()
    (ev / "run-1.json").write_text("{}", encoding="utf-8")

    result = pre_hook.pre_compact({"repo_root": str(tmp_path)})

    assert result["ok"] is True, result
    assert isinstance(result["checkpointed"], list), result
    assert result["checkpointed"], "checkpointed list must be non-empty"
    assert "feature_list.json" in result["checkpointed"], result
    # The other two durable artifacts are checkpointed too.
    assert "claude-progress.txt" in result["checkpointed"], result
    assert any("evidence" in p for p in result["checkpointed"]), result


def test_pre_compact_feature_list_via_state_override(tmp_path):
    feat = tmp_path / "nested" / "feature_list.json"
    feat.parent.mkdir(parents=True)
    feat.write_text(json.dumps({"items": []}), encoding="utf-8")
    result = pre_hook.pre_compact(
        {"repo_root": str(tmp_path), "feature_list": str(feat)}
    )
    assert result["ok"] is True, result
    assert any(p.endswith("feature_list.json") for p in result["checkpointed"]), result


def test_pre_compact_ok_true_even_when_artifacts_missing(tmp_path):
    """A missing artifact is recorded, not raised — ok stays True (non-blocking)."""
    result = pre_hook.pre_compact({"repo_root": str(tmp_path)})
    assert result["ok"] is True, result
    assert "feature_list.json" in result.get("missing", []), result


def test_pre_compact_main_shell_exits_nonblocking():
    """PreCompact main must exit 0 — it can never block compaction."""
    rc = _run_main_with_stdin(pre_hook, json.dumps({}))
    assert rc == 0, rc


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
