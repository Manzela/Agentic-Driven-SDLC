#!/usr/bin/env python3
"""PostToolUse hook — next-turn feedback only (non-blocking).

By contract PostToolUse CANNOT gate (it runs after the tool already executed).
It surfaces advisory signals for the next turn (in Phase 1 it runs
ESLint/tsc/Semgrep/dead-code on changed files). Exit code is always 0 — it must
never block. Pure importable core (`evaluate`) + thin stdin shell (`main`).
"""
from __future__ import annotations
import json
import sys


def evaluate(event: dict) -> dict:
    """Return an advisory note for the next turn. Never blocks."""
    changed = (event or {}).get("tool_input", {}).get("file_path", "")
    return {"decision": "advise", "note": f"PostToolUse observed change: {changed}" if changed else "PostToolUse: no file change"}


def main() -> int:
    raw = sys.stdin.read()
    try:
        event = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        event = {}
    print(json.dumps(evaluate(event)))
    return 0  # never gates


if __name__ == "__main__":
    sys.exit(main())
