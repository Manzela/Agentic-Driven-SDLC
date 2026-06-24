"""PostToolUse wiring runner fix (§2.5 / Task 11 / RT-06) + mypy runner.

The live hook imported a NONEXISTENT `check_wiring` (so the wiring leg silently always
returned []). The fix uses analyze + emit_wiring_items and NORMALIZES the emitted
CoverageItems (nested wiring:{file,line}) to feedback shape {source,severity,path,line,
rule,message} — never a stringified dict. PostToolUse never blocks (exit 0).
"""
from __future__ import annotations

import importlib.util
import io
import json
import pathlib
import textwrap

ROOT = pathlib.Path(__file__).resolve().parents[2]


def _load():
    spec = importlib.util.spec_from_file_location(
        "post_tool_use_hook", ROOT / ".claude/hooks/post_tool_use_hook.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_real_wiring_imports_analyze_and_emit(tmp_path):
    m = _load()
    mod = tmp_path / "dummy.py"
    mod.write_text("def f(): pass\n", encoding="utf-8")
    assert isinstance(m._real_wiring([str(mod)]), list)


def test_real_wiring_output_shape_normalized_to_feedback(tmp_path):
    m = _load()
    src = textwrap.dedent("""\
        def used():
            pass

        def unused():
            pass

        used()
    """)
    mod = tmp_path / "fixture.py"
    mod.write_text(src, encoding="utf-8")
    result = m._real_wiring([str(mod)])
    assert isinstance(result, list)
    for item in result:
        assert isinstance(item, dict)
        assert item.get("source") == "wiring"
        assert "severity" in item
        assert "path" in item            # wiring.file -> path
        assert "line" in item            # wiring.line -> line
        assert "rule" in item
        message = str(item.get("message", ""))
        assert message and not message.startswith("{"), f"message is a stringified dict: {message}"


def test_real_wiring_unreachable_symbol_in_feedback(tmp_path):
    m = _load()
    src = textwrap.dedent("""\
        def used():
            return 42

        def unused_orphan():
            return "never called"

        result = used()
    """)
    mod = tmp_path / "fixture.py"
    mod.write_text(src, encoding="utf-8")
    messages = [it.get("message", "") for it in m._real_wiring([str(mod)])]
    assert any("unused_orphan" in msg or "unreachable" in msg.lower() for msg in messages), messages


def test_post_tool_use_with_wiring_feedback_exits_zero_nonblock(tmp_path):
    m = _load()
    mod = tmp_path / "fixture.py"
    mod.write_text("def unused_orphan():\n    pass\n", encoding="utf-8")
    result = m.post_tool_use({"tool_name": "Write", "tool_input": {"file_path": str(mod)}})
    assert result["decision"] == "non_block"
    assert any(f.get("source") == "wiring" for f in result.get("feedback", [])), result


def test_main_returns_zero_with_wiring_finding(tmp_path, monkeypatch, capsys):
    m = _load()
    mod = tmp_path / "fixture.py"
    mod.write_text("def unused():\n    pass\n", encoding="utf-8")
    event = {"tool_name": "Write", "tool_input": {"file_path": str(mod)}, "session_id": "s"}
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(event)))
    assert m.main() == 0
    captured = capsys.readouterr()
    if captured.out.strip():
        out = json.loads(captured.out)
        assert out["hookSpecificOutput"]["hookEventName"] == "PostToolUse"
        assert "additionalContext" in out["hookSpecificOutput"]


def test_wiring_non_py_paths_skipped(tmp_path):
    m = _load()
    doc = tmp_path / "README.md"
    doc.write_text("# docs\n", encoding="utf-8")
    assert m._real_wiring([str(doc)]) == []


def test_mypy_runner_registered():
    m = _load()
    runners = m._default_runners()
    assert "mypy" in runners
    assert callable(runners["mypy"])


def test_mypy_fail_open_without_binary(tmp_path):
    """mypy is not installed here; the runner must fail-OPEN (return [], never raise)."""
    m = _load()
    mod = tmp_path / "m.py"
    mod.write_text("x: int = 'not an int'\n", encoding="utf-8")
    result = m._real_mypy([str(mod)])
    assert isinstance(result, list)  # [] when mypy absent; advisory-only, never raises


def test_mypy_non_py_paths_skipped(tmp_path):
    m = _load()
    assert m._real_mypy([str(tmp_path / "README.md")]) == []


def test_mypy_runner_actually_invoked(tmp_path):
    """F6 (red-team): registration is not enough — post_tool_use must INVOKE the mypy
    runner. A custom runner records its call and its source appears in the feedback."""
    m = _load()
    called = {"n": 0}

    def fake_mypy(paths):
        called["n"] += 1
        return [{"source": "mypy", "severity": "error", "path": paths[0],
                 "line": 1, "rule": "mypy", "message": "fake type error"}]

    mod = tmp_path / "m.py"
    mod.write_text("x = 1\n", encoding="utf-8")
    runners = {**m._default_runners(), "mypy": fake_mypy}
    result = m.post_tool_use({"tool_name": "Write", "tool_input": {"file_path": str(mod)}}, runners=runners)
    assert called["n"] == 1, "mypy runner was registered but never invoked"
    assert any(f.get("source") == "mypy" for f in result["feedback"])


def test_mypy_parser_maps_severities(tmp_path, monkeypatch):
    """F2/F3: parse real-shaped mypy stdout — error->error, note->info, indented note's
    path is clean. mypy is faked via a stub on PATH so the parser runs."""
    import subprocess
    m = _load()
    mod = tmp_path / "m.py"
    mod.write_text("x: int = 'no'\n", encoding="utf-8")
    sample = (f"{mod}:1:10: error: Incompatible types [assignment]\n"
              f'{mod}:2: note: Revealed type is "builtins.str"\n'   # standalone note -> info
              f"    {mod}:1: note: indented continuation\n")        # indented -> skipped (F3)

    class _Proc:
        stdout = sample
        returncode = 1

    monkeypatch.setattr(m.shutil if hasattr(m, "shutil") else __import__("shutil"),
                        "which", lambda _b: "/usr/bin/mypy")
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: _Proc())
    findings = m._real_mypy([str(mod)])
    by_sev = {f["severity"] for f in findings}
    assert "error" in by_sev
    assert "info" in by_sev                                   # note -> info, not warning
    assert all(not f["path"].startswith(" ") for f in findings)  # no leading-space path
