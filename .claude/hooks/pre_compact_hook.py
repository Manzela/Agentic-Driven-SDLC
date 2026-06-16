#!/usr/bin/env python3
"""PreCompact hook — checkpoint the proven/unproven tally before context trim.

Non-blocking (exit 0). Writes a small checkpoint so a long autonomous run can
rehydrate its burn-down after compaction (SessionStart reads it back). Pure
importable core (`checkpoint`) + thin stdin shell (`main`).
"""
from __future__ import annotations
import json
import sys
from pathlib import Path


def checkpoint(feature_list: dict) -> dict:
    items = (feature_list or {}).get("items", [])
    in_scope = [i for i in items if i.get("in_scope")]
    proven = sum(1 for i in in_scope if i.get("status") == "proven")
    return {"proven": proven, "total": len(in_scope)}


def main() -> int:
    raw = sys.stdin.read()
    try:
        event = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        event = {}
    snap = checkpoint(event.get("feature_list") or {})
    run = Path(__file__).resolve().parents[2] / ".claude" / "run"
    run.mkdir(parents=True, exist_ok=True)
    (run / "checkpoint.json").write_text(json.dumps(snap))
    print(json.dumps(snap))
    return 0


if __name__ == "__main__":
    sys.exit(main())
