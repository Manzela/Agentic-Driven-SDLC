"""Actor-independence fix #4: field-level write authority at PreToolUse."""
import importlib.util
import pathlib

_p = pathlib.Path(__file__).resolve().parents[2] / ".claude/hooks/pre_tool_use_hook.py"
_spec = importlib.util.spec_from_file_location("pre_tool_use_hook", _p)
hook = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hook)

FL = "apps/web/feature_list.json"


def test_status_write_by_implementer_blocked():
    out = hook.evaluate(tool_input={"file_path": FL, "field": "status"},
                        resolved_actor="implementer.md", human_signed=False)
    assert out["decision"] == "block" and "status" in out["reason"].lower()


def test_status_write_by_verifier_allowed():
    out = hook.evaluate(tool_input={"file_path": FL, "field": "status"},
                        resolved_actor="verifier.md", human_signed=False)
    assert out["decision"] == "allow"


def test_in_scope_requires_human():
    out = hook.evaluate(tool_input={"file_path": FL, "field": "in_scope"},
                        resolved_actor="verifier.md", human_signed=False)
    assert out["decision"] == "block" and "in_scope" in out["reason"].lower()
    ok = hook.evaluate(tool_input={"file_path": FL, "field": "in_scope"},
                       resolved_actor="verifier.md", human_signed=True)
    assert ok["decision"] == "allow"


def test_protected_artifact_blocked_for_agent():
    out = hook.evaluate(tool_input={"file_path": "tests/spine/test_stop_hook.py"},
                        resolved_actor="implementer.md", human_signed=False)
    assert out["decision"] == "block" and "protected" in out["reason"].lower()


def test_protected_artifact_allowed_for_main():
    out = hook.evaluate(tool_input={"file_path": "tests/spine/test_stop_hook.py"},
                        resolved_actor="main", human_signed=False)
    assert out["decision"] == "allow"
