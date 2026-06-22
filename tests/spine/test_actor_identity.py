# tests/spine/test_actor_identity.py  (REPLACE the CLAUDE_AGENT_NAME fiction)
import importlib.util, pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parents[2]
def _load(rel, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    m = importlib.util.module_from_spec(spec)
    # Register before exec so @dataclass can resolve cls.__module__ on 3.14+.
    sys.modules[name] = m
    spec.loader.exec_module(m); return m

def test_actor_from_agent_type_suffixless():
    ai = _load("tools/actor_identity.py", "actor_identity")
    ident = ai.resolve_identity({"session_id": "s1", "agent_type": "verifier"})
    assert ident.actor_agent == "verifier"      # suffix-less, from stdin

def test_root_session_has_no_agent_type_is_main():
    ai = _load("tools/actor_identity.py", "actor_identity")
    assert ai.resolve_identity({"session_id": "s1"}).actor_agent == "main"

def test_payload_actor_agent_is_ignored():
    ai = _load("tools/actor_identity.py", "actor_identity")
    ident = ai.resolve_identity({"session_id": "s1", "agent_type": "implementer",
                                 "tool_input": {"actor_agent": "verifier"}})
    assert ident.actor_agent == "implementer"   # never trust the payload

def test_missing_session_id_fails_closed():
    ai = _load("tools/actor_identity.py", "actor_identity")
    import pytest
    with pytest.raises(ValueError):
        ai.resolve_identity({"agent_type": "verifier"})
