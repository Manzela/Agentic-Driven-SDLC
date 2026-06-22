#!/usr/bin/env python3
"""Hook stdout schema conformance (Task 7c — Stage-0 capstone).

Asserts every hook's ALLOW / SUCCESS / FEEDBACK path emits stdout that Claude
Code's hook-output schema accepts (https://code.claude.com/docs/en/hooks):

  * PreToolUse  allow  → exit 0, NO stdout (or hookSpecificOutput.permissionDecision);
                         NEVER a bare {"decision":"allow"}.
  * PostToolUse no-issue→ exit 0, NO stdout; feedback only via
                         hookSpecificOutput.additionalContext; NEVER {"decision":"non_block"}.
                         A missing linter binary is SKIPPED SILENTLY (no os-error feedback).
  * Stop        allow  → exit 0; reason (if any) only via hookSpecificOutput.additionalContext;
                         NEVER a bare top-level "decision".
  * SubagentStop accept→ exit 0, NO stdout (already correct — guarded here).
  * SessionStart       → exit 0; context ONLY via hookSpecificOutput.additionalContext;
                         NEVER bare top-level "summary"/"decision".
  * PreCompact         → exit 0; NO stdout (or schema-valid only); NEVER a bare
                         {"checkpointed":...} payload.

These tests run each hook as a real subprocess (the live failure mode is the
stdout the subprocess emits, not the importable core's return value). The pure
cores keep their existing return shapes — only the main() output paths are under
test here.
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]

# Top-level keys that, if present in stdout JSON, mean the hook emitted a
# homegrown / invalid contract. The ONLY schema-valid wrapper is
# "hookSpecificOutput"; a top-level "decision":"allow"/"non_block" (or any bare
# product payload like "checkpointed"/"summary"/"terminal") is INVALID INPUT.
_INVALID_TOP_LEVEL = ("decision", "checkpointed", "terminal", "summary",
                      "unproven_count", "proven_count", "feedback")


def _run(hook: str, event: dict, env: dict | None = None):
    e = {**os.environ, **(env or {})}
    p = subprocess.run(
        [sys.executable, str(ROOT / ".claude/hooks" / hook)],
        input=json.dumps(event), capture_output=True, text=True,
        cwd=str(ROOT), env=e,
    )
    return p.returncode, p.stdout.strip(), p.stderr.strip()


def _assert_schema_valid_or_empty(out: str):
    """stdout must be empty, OR a JSON object whose only governance-bearing
    top-level key is 'hookSpecificOutput' (never a bare decision/payload)."""
    if out == "":
        return
    data = json.loads(out)  # must be valid JSON if non-empty
    assert isinstance(data, dict), out
    for k in _INVALID_TOP_LEVEL:
        assert k not in data, f"invalid top-level key {k!r} in stdout: {out}"


# ── PreToolUse ───────────────────────────────────────────────────────────────

def test_pretooluse_allow_emits_no_invalid_json():
    rc, out, err = _run("pre_tool_use_hook.py", {
        "session_id": "s", "agent_type": "main", "tool_name": "Bash",
        "tool_input": {"command": "ls"}})
    assert rc == 0
    assert '"decision"' not in out  # never a bare {"decision":"allow"}
    assert out == "" or '"permissionDecision"' in out
    _assert_schema_valid_or_empty(out)


def test_pretooluse_coverage_allow_emits_no_invalid_json():
    rc, out, err = _run("pre_tool_use_hook.py", {
        "session_id": "s", "agent_type": "verifier", "tool_name": "Edit",
        "tool_input": {"file_path": "feature_list.json",
                       "old_string": '{"items":[{"id":"X","in_scope":true,"status":"unproven"}]}',
                       "new_string": '{"items":[{"id":"X","in_scope":true,"status":"proven"}]}'}})
    assert rc == 0
    assert '"decision"' not in out
    _assert_schema_valid_or_empty(out)


# ── PostToolUse ──────────────────────────────────────────────────────────────

def test_posttooluse_noissue_emits_no_decision_field():
    rc, out, err = _run("post_tool_use_hook.py", {
        "session_id": "s", "tool_name": "Edit",
        "tool_input": {"file_path": "x.py"}})
    assert '"non_block"' not in out
    assert out == "" or '"hookSpecificOutput"' in out
    _assert_schema_valid_or_empty(out)


def test_posttooluse_no_paths_emits_no_stdout():
    """A non-edit tool produces no findings → no stdout at all."""
    rc, out, err = _run("post_tool_use_hook.py", {
        "session_id": "s", "tool_name": "Read", "tool_input": {"file_path": "x.py"}})
    assert out == "", out
    _assert_schema_valid_or_empty(out)


def test_posttooluse_missing_linter_skipped_silently():
    """When a linter binary is absent (os error 2), no feedback is emitted —
    the no-issue path stays empty rather than surfacing a runner error."""
    rc, out, err = _run("post_tool_use_hook.py", {
        "session_id": "s", "tool_name": "Edit",
        "tool_input": {"file_path": "x.py"}})
    assert "os error 2" not in out and "No such file" not in out
    _assert_schema_valid_or_empty(out)


# ── Stop ─────────────────────────────────────────────────────────────────────

def test_stop_allow_emits_no_bare_decision():
    rc, out, err = _run("stop_hook.py", {
        "run_state": {"violation_count": 1, "block_streak": 5},
        "feature_list": {"items": [{"id": "X", "in_scope": True, "status": "unproven"}]}})
    assert rc == 0
    assert '"decision"' not in out
    # The HANDOFF steering must still reach the agent — via additionalContext.
    assert "HANDOFF" in (out + err)
    _assert_schema_valid_or_empty(out)


def test_stop_complete_emits_schema_valid():
    rc, out, err = _run("stop_hook.py", {
        "run_state": {"violation_count": 0},
        "feature_list": {"items": [{"id": "X", "in_scope": True, "status": "proven"}]}})
    assert rc == 0
    assert '"decision"' not in out
    _assert_schema_valid_or_empty(out)


# ── SubagentStop ─────────────────────────────────────────────────────────────

def test_subagentstop_accept_emits_no_stdout():
    rc, out, err = _run("subagent_stop_hook.py", {
        "session_id": "s", "agent_type": "implementer", "tool_input": {}})
    assert rc == 0 and out == ""


# ── SessionStart ─────────────────────────────────────────────────────────────

def test_sessionstart_emits_only_hook_specific_output():
    rc, out, err = _run("session_start_hook.py", {})
    assert rc == 0
    _assert_schema_valid_or_empty(out)
    if out:
        data = json.loads(out)
        assert "hookSpecificOutput" in data, out
        hso = data["hookSpecificOutput"]
        assert hso.get("hookEventName") == "SessionStart", out
        assert "additionalContext" in hso, out


# ── PreCompact ───────────────────────────────────────────────────────────────

def test_precompact_emits_no_invalid_payload():
    rc, out, err = _run("pre_compact_hook.py", {})
    assert rc == 0
    assert '"checkpointed"' not in out
    _assert_schema_valid_or_empty(out)
