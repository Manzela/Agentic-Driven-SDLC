"""actor_identity.py — resolve the acting agent identity from RUNTIME signals only.

Actor-independence fix #1. The writing agent must never be able to declare its
own identity inside an evidence record. Identity is derived from the hook stdin
JSON ``agent_type`` field (set by Claude Code when a subagent is spawned; it is
SUFFIX-LESS, e.g. ``"verifier"``, and absent for the root session) plus the hook
stdin ``session_id`` — NEVER from a field the writing agent places in the tool
payload. There is NO ``CLAUDE_AGENT_NAME`` environment variable; never read one.

Pure stdlib. Imported by the SubagentStop and PreToolUse hooks; both stamp the
resolved identity over whatever the agent supplied, so a forged ``actor_agent``
in an evidence record cannot promote a self-graded flip to ``proven``.
"""

from __future__ import annotations

import sys
import pathlib
from dataclasses import dataclass

# Ensure ``from tools.spine_roles import ...`` resolves when this module is run
# as a hook subprocess (repo root on the path).
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from tools.spine_roles import MAIN_ACTOR  # noqa: E402

__all__ = ["Identity", "resolve_identity"]


@dataclass(frozen=True)
class Identity:
    session_id: str
    actor_agent: str


def resolve_identity(hook_input: dict) -> Identity:
    """Resolve {session_id, actor_agent} from the runtime, not the payload.

    ``session_id`` comes from the hook stdin event (the harness supplies it).
    ``actor_agent`` comes from the hook stdin ``agent_type`` field that Claude
    Code sets per subagent invocation (suffix-less, e.g. ``"verifier"``); the
    root session omits it and resolves to ``"main"``. Any ``actor_agent`` /
    ``*_session_id`` keys inside ``hook_input`` (or nested ``tool_input``) are
    deliberately IGNORED — they are agent-supplied and untrusted.

    Raises ``ValueError`` if no ``session_id`` is present (fail closed: an
    unidentifiable actor cannot be granted write authority).
    """
    session_id = hook_input.get("session_id")
    if not session_id:
        raise ValueError("hook_input missing required runtime 'session_id'")
    # Claude Code supplies the subagent identity in the hook stdin JSON as
    # `agent_type` (suffix-less, e.g. "verifier"); the root session omits it.
    # There is NO CLAUDE_AGENT_NAME env var — never read one.
    actor_agent = hook_input.get("agent_type") or MAIN_ACTOR
    return Identity(session_id=str(session_id), actor_agent=str(actor_agent))
