"""Actor-independence fix #1: identity comes from the runtime, not the payload."""
import pytest
from tools.actor_identity import resolve_identity


def test_actor_from_env_not_payload(monkeypatch):
    monkeypatch.setenv("CLAUDE_AGENT_NAME", "implementer.md")
    # forged actor_agent + session fields in the payload must be ignored
    ident = resolve_identity({"session_id": "sess-abc", "actor_agent": "verifier.md"})
    assert ident.actor_agent == "implementer.md"
    assert ident.session_id == "sess-abc"


def test_missing_agent_defaults_to_main(monkeypatch):
    monkeypatch.delenv("CLAUDE_AGENT_NAME", raising=False)
    assert resolve_identity({"session_id": "s1"}).actor_agent == "main"


def test_missing_session_fails_closed():
    with pytest.raises(ValueError):
        resolve_identity({})
