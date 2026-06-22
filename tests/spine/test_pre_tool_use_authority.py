"""Actor-independence fix #4: field-level write authority at PreToolUse.

Contract (Task 2): authority is detected by DIFFING the JSON (old_string vs
new_string for Edit; on-disk vs content for Write), not by a phantom ``field``
key. ``evaluate`` takes ``tool_name``; ``human_signed`` is resolved out-of-band
from the ``HUMAN_SIGNED`` env var, never from the tool payload. On a BLOCK the
hook writes the reason to STDERR and exits 2 (no JSON to stdout).
"""
import hashlib  # noqa: F401  (kept for parity with sibling spine tests)
import importlib.util
import json
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
HOOK = ROOT / ".claude/hooks/pre_tool_use_hook.py"

_p = ROOT / ".claude/hooks/pre_tool_use_hook.py"
_spec = importlib.util.spec_from_file_location("pre_tool_use_hook", _p)
hook = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hook)

FL = "apps/web/feature_list.json"

_OLD = '{"items":[{"id":"X","in_scope":true,"status":"unproven"}]}'
_NEW = '{"items":[{"id":"X","in_scope":true,"status":"proven"}]}'


def _run(event: dict, env: dict | None = None):
    e = {**os.environ, **(env or {})}
    p = subprocess.run([sys.executable, str(HOOK)], input=json.dumps(event),
                       capture_output=True, text=True, env=e, cwd=str(ROOT))
    return p.returncode, p.stdout, p.stderr


# --- Real-payload subprocess behaviors (Task 2 contract) -------------------

def test_real_edit_status_flip_by_implementer_blocks():
    rc, out, err = _run({"session_id": "s", "agent_type": "implementer", "tool_name": "Edit",
        "tool_input": {"file_path": "feature_list.json", "old_string": _OLD, "new_string": _NEW}})
    assert rc == 2 and "verifier" in err            # blocked, reason on STDERR


def test_real_edit_status_flip_by_verifier_allows():
    rc, out, err = _run({"session_id": "s", "agent_type": "verifier", "tool_name": "Edit",
        "tool_input": {"file_path": "feature_list.json", "old_string": _OLD, "new_string": _NEW}})
    assert rc == 0


def test_bash_redirect_to_protected_path_blocks():
    rc, out, err = _run({"session_id": "s", "agent_type": "implementer", "tool_name": "Bash",
        "tool_input": {"command": "echo x > tests/spine/x.py"}})
    assert rc == 2 and "tests/" in err


def test_in_scope_flip_with_payload_human_signed_but_no_env_blocks():
    rc, out, err = _run({"session_id": "s", "agent_type": "implementer", "tool_name": "Edit",
        "tool_input": {"file_path": "feature_list.json",
                       "old_string": '{"items":[{"id":"X","in_scope":false}]}',
                       "new_string": '{"items":[{"id":"X","in_scope":true}]}',
                       "human_signed": True}})   # forged in payload
    assert rc == 2


def test_in_scope_flip_with_HUMAN_SIGNED_env_allows():
    rc, out, err = _run({"session_id": "s", "agent_type": "implementer", "tool_name": "Edit",
        "tool_input": {"file_path": "feature_list.json",
                       "old_string": '{"items":[{"id":"X","in_scope":false}]}',
                       "new_string": '{"items":[{"id":"X","in_scope":true}]}'}},
        env={"HUMAN_SIGNED": "true"})
    assert rc == 0


# --- Pure-core evaluate() behaviors (migrated to JSON-delta contract) -------

def test_status_write_by_implementer_blocked():
    out = hook.evaluate(tool_name="Edit",
                        tool_input={"file_path": FL, "old_string": _OLD, "new_string": _NEW},
                        resolved_actor="implementer", human_signed=False)
    assert out["decision"] == "block" and "status" in out["reason"].lower()


def test_status_write_by_verifier_allowed():
    out = hook.evaluate(tool_name="Edit",
                        tool_input={"file_path": FL, "old_string": _OLD, "new_string": _NEW},
                        resolved_actor="verifier", human_signed=False)
    assert out["decision"] == "allow"


def test_in_scope_requires_human():
    old = '{"items":[{"id":"X","in_scope":false}]}'
    new = '{"items":[{"id":"X","in_scope":true}]}'
    out = hook.evaluate(tool_name="Edit",
                        tool_input={"file_path": FL, "old_string": old, "new_string": new},
                        resolved_actor="verifier", human_signed=False)
    assert out["decision"] == "block" and "in_scope" in out["reason"].lower()
    ok = hook.evaluate(tool_name="Edit",
                       tool_input={"file_path": FL, "old_string": old, "new_string": new},
                       resolved_actor="verifier", human_signed=True)
    assert ok["decision"] == "allow"


def test_benign_edit_does_not_block():
    old = '{"items":[{"id":"F-1","status":"unproven","in_scope":true,"acceptance_criteria":[]}]}'
    new = '{"items":[{"id":"F-1","status":"unproven","in_scope":true,"acceptance_criteria":["x"]}]}'
    out = hook.evaluate(tool_name="Edit",
                        tool_input={"file_path": FL, "old_string": old, "new_string": new},
                        resolved_actor="implementer", human_signed=False)
    assert out["decision"] == "allow"          # no field move → no deny


def test_protected_artifact_blocked_for_agent():
    out = hook.evaluate(tool_name="Edit",
                        tool_input={"file_path": "tests/spine/test_stop_hook.py"},
                        resolved_actor="implementer", human_signed=False)
    assert out["decision"] == "block" and "tests/" in out["reason"]


def test_protected_artifact_allowed_for_main():
    out = hook.evaluate(tool_name="Edit",
                        tool_input={"file_path": "tests/spine/test_stop_hook.py"},
                        resolved_actor="main", human_signed=False)
    assert out["decision"] == "allow"


def test_bash_write_targets_parses_redirect_and_tee():
    assert "a.py" in hook._bash_write_targets("echo x > a.py")
    assert "b.py" in hook._bash_write_targets("echo x >> b.py")
    assert "c.py" in hook._bash_write_targets("echo x | tee c.py")
    assert "d.py" in hook._bash_write_targets("echo x | tee -a d.py")
