# tests/spine/test_spine_roles.py
import importlib.util, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[2]

def _load(rel, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

def test_roles_are_suffixless_single_source():
    r = _load("tools/spine_roles.py", "spine_roles")
    assert r.VERIFIER_ROLE == "verifier"           # NOT "verifier.md"
    assert r.MAIN_ACTOR == "main"
    assert "tests/" in r.PROTECTED_PREFIXES
    assert ".claude/settings.json" in r.PROTECTED_PREFIXES
