"""spine_roles.py — single source of actor role names + protected paths (COH-1).

Role names match the Claude Code subagent `agent_type` (the frontmatter `name:`),
which is SUFFIX-LESS — there is no `.md`. Every hook/tool that enforces authority
imports from here so a roster change is one edit, not four.
"""
from __future__ import annotations

VERIFIER_ROLE = "verifier"
IMPLEMENTER_ROLE = "implementer"
INITIALIZER_ROLE = "initializer"
RESEARCH_ROLE = "research"
MAIN_ACTOR = "main"

PROTECTED_PREFIXES: tuple[str, ...] = (
    "tests/", "schema/", ".github/workflows/", ".github/policies/",
    ".claude/hooks/", ".claude/settings.json",
)
