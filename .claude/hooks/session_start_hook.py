#!/usr/bin/env python3
"""SessionStart hook — restore run state at session start (non-blocking).

Reads the PreCompact checkpoint (if any) and the coverage tally, and surfaces a
summary for context. NEVER blocks (exit 0); the PreToolUse integrity guard is
the enforcement point. Pure importable core (`session_start`) + stdin shell.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path


def session_start(feature_list: dict, checkpoint: dict | None) -> dict:
    items = (feature_list or {}).get("items", [])
    in_scope = [i for i in items if i.get("in_scope")]
    proven = sum(1 for i in in_scope if i.get("status") == "proven")
    summary = {"proven_count": proven, "unproven_count": len(in_scope) - proven,
               "resumed_from_checkpoint": bool(checkpoint)}
    return summary


def main() -> int:
    raw = sys.stdin.read()
    try:
        event = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        event = {}
    cp_path = Path(__file__).resolve().parents[2] / ".claude" / "run" / "checkpoint.json"
    checkpoint = json.loads(cp_path.read_text()) if cp_path.exists() else None
    print(json.dumps(session_start(event.get("feature_list") or {}, checkpoint)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
