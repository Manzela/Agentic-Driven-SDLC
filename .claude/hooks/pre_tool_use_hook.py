#!/usr/bin/env python3
"""PreToolUse gate — field-level write authority (actor-independence fix #4).

The only true prevention gate (exit 2 blocks before a write lands). Enforces:

  * the coverage model's ``status`` field is writable ONLY by the verifier
    (a runtime-resolved actor of ``verifier.md``);
  * the coverage model's ``in_scope`` field is mutable ONLY by a human-signed
    change (an autonomous agent cannot self-exempt an item to fake COMPLETE);
  * protected artifacts (tests, schema, CI, hooks, coverage schema) may not be
    edited by an agent (only the root ``main`` session / a human).

Identity is resolved by tools/actor_identity (fix #1), never from the payload.
PURE importable core (`evaluate`) + thin stdin shell (`main`). Fails closed.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

VERIFIER_AGENT = "verifier.md"

PROTECTED_PREFIXES = (
    "tests/", "schema/", ".github/workflows/", ".github/policies/",
    ".claude/hooks/", ".claude/settings.json",
)


def evaluate(*, tool_input: dict, resolved_actor: str, human_signed: bool) -> dict:
    """Return {"decision": "allow"|"block", "reason": str}."""
    try:
        path = (tool_input or {}).get("file_path", "") or ""
        field = (tool_input or {}).get("field")

        # Coverage-model field authority.
        if path.endswith("feature_list.json"):
            if field == "status" and resolved_actor != VERIFIER_AGENT:
                return {"decision": "block",
                        "reason": f"status is writable only by {VERIFIER_AGENT} (actor={resolved_actor})"}
            if field == "in_scope" and not human_signed:
                return {"decision": "block",
                        "reason": "in_scope is mutable only via a human-signed change"}
            return {"decision": "allow", "reason": "coverage-model write permitted"}

        # Protected-artifact guard: agents may not edit tests/schema/CI/hooks.
        if resolved_actor != "main" and any(path.startswith(p) for p in PROTECTED_PREFIXES):
            return {"decision": "block",
                    "reason": f"protected artifact may not be edited by an agent: {path}"}

        return {"decision": "allow", "reason": "write permitted"}
    except Exception as exc:  # noqa: BLE001 — fail closed.
        return {"decision": "block", "reason": f"pre_tool_use raised {type(exc).__name__}: {exc}"}


def main() -> int:
    raw = sys.stdin.read()
    try:
        event = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        print(json.dumps({"decision": "block", "reason": "unparseable event"}))
        return 2
    from tools.actor_identity import resolve_identity
    try:
        actor = resolve_identity(event).actor_agent
    except ValueError as exc:
        print(json.dumps({"decision": "block", "reason": str(exc)}))
        return 2
    ti = event.get("tool_input", {})
    decision = evaluate(tool_input=ti, resolved_actor=actor,
                        human_signed=bool(ti.get("human_signed", False)))
    print(json.dumps(decision))
    return 0 if decision["decision"] == "allow" else 2


if __name__ == "__main__":
    sys.exit(main())
