"""actor_identity.py — resolve the acting agent identity from RUNTIME signals only.

Actor-independence fix #1. The writing agent must never be able to declare its
own identity inside an evidence record. Identity is derived from the harness-
supplied environment variable ``CLAUDE_AGENT_NAME`` (set when a subagent is
spawned; absent/``main`` for the root session) and the hook stdin ``session_id``
— NEVER from a field the writing agent places in the tool payload.

Pure stdlib. Imported by the SubagentStop and PreToolUse hooks; both stamp the
resolved identity over whatever the agent supplied, so a forged ``actor_agent``
in an evidence record cannot promote a self-graded flip to ``proven``.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

__all__ = ["Identity", "resolve_identity"]


@dataclass(frozen=True)
class Identity:
    session_id: str
    actor_agent: str


def resolve_identity(hook_input: dict) -> Identity:
    """Resolve {session_id, actor_agent} from the runtime, not the payload.

    ``session_id`` comes from the hook stdin event (the harness supplies it).
    ``actor_agent`` comes from the ``CLAUDE_AGENT_NAME`` environment variable
    that the harness sets per subagent invocation; the root session resolves to
    ``"main"``. Any ``actor_agent`` / ``*_session_id`` keys inside ``hook_input``
    (or nested ``tool_input``) are deliberately IGNORED — they are agent-supplied
    and untrusted.

    Raises ``ValueError`` if no ``session_id`` is present (fail closed: an
    unidentifiable actor cannot be granted write authority).
    """
    session_id = hook_input.get("session_id")
    if not session_id:
        raise ValueError("hook_input missing required runtime 'session_id'")
    actor_agent = os.environ.get("CLAUDE_AGENT_NAME") or "main"
    return Identity(session_id=str(session_id), actor_agent=str(actor_agent))
