"""hook_telemetry.py — append-only record that a hook fired (canary evidence)."""
from __future__ import annotations
import json, os, sys
def record_fire(hook_event: str, session_id: str, **extra) -> None:
    sink = os.environ.get("SPINE_HOOK_TELEMETRY")
    if not sink:
        return
    rec = {"hook_event": hook_event, "session_id": session_id,
           "command_path": (sys.argv[0] if sys.argv else ""), **extra}
    try:
        with open(sink, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")
    except OSError:
        pass
