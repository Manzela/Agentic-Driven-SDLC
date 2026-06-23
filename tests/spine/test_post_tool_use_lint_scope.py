"""PostToolUse lint must target Python files only (ruff is a Python linter)."""
import importlib.util
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]


def _load():
    spec = importlib.util.spec_from_file_location(
        "pth", ROOT / ".claude/hooks/post_tool_use_hook.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_real_lint_skips_non_python_files():
    m = _load()
    # A markdown/json/text edit must NOT be linted as Python (no ruff run).
    assert m._real_lint(["README.md"]) == []
    assert m._real_lint(["notes.txt", "data.json"]) == []


def test_real_lint_only_passes_py_paths_to_ruff(monkeypatch):
    m = _load()
    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        return []

    monkeypatch.setattr(m, "_run_subprocess", fake_run)
    m._real_lint(["a.md", "b.py", "c.json"])
    assert "b.py" in captured["cmd"]
    assert "a.md" not in captured["cmd"] and "c.json" not in captured["cmd"]


def test_post_tool_use_on_markdown_emits_no_syntax_findings():
    m = _load()
    out = m.post_tool_use({"tool_name": "Edit", "tool_input": {"file_path": "doc.md"}})
    assert out["decision"] == "non_block"
    assert all("SyntaxError" not in (f.get("message", "") or "") for f in out["feedback"])
