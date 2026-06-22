"""run_state_driver.py — the missing loop driver: maintain run_state.json on disk
so the Stop hook gates on REAL counters (not the streak-0 fallback).

Keys written match what the Stop hook reads:
  iteration_count, no_progress_n, block_streak, violation_count,
  external_blocker, status, session_id, budget_exceeded.
"""
from __future__ import annotations

import json
from pathlib import Path


def _path(root: Path | str) -> Path:
    return Path(root) / "run_state.json"


def init(root: Path | str, session_id: str) -> dict:
    """Write a fresh run_state.json at *root* and return it."""
    row: dict = {
        "session_id": session_id,
        "iteration_count": 0,
        "no_progress_n": 0,
        "block_streak": 0,
        "violation_count": 0,
        "budget_exceeded": False,
        "external_blocker": None,
        "status": "running",
    }
    _path(root).write_text(json.dumps(row, indent=2))
    return row


def tick(
    root: Path | str,
    *,
    made_progress: bool,
    violation_count: int,
    external_blocker: str | None = None,
    budget_exceeded: bool = False,
) -> dict:
    """Advance counters, persist, and return the updated row.

    - iteration_count always increments.
    - no_progress_n resets to 0 on progress, otherwise increments.
    - block_streak resets to 0 on progress; increments by 1 when there
      was no progress AND violation_count > 0.
    - violation_count is overwritten with the supplied value.
    - external_blocker is overwritten (None clears it).
    - budget_exceeded is overwritten with the supplied value.
    """
    p = _path(root)
    row: dict = json.loads(p.read_text()) if p.is_file() else init(root, "unknown")

    row["iteration_count"] = row.get("iteration_count", 0) + 1

    if made_progress:
        row["no_progress_n"] = 0
        row["block_streak"] = 0
    else:
        row["no_progress_n"] = row.get("no_progress_n", 0) + 1
        row["block_streak"] = row.get("block_streak", 0) + (1 if violation_count else 0)

    row["violation_count"] = int(violation_count)
    row["external_blocker"] = external_blocker
    row["budget_exceeded"] = bool(budget_exceeded)

    p.write_text(json.dumps(row, indent=2))
    return row
