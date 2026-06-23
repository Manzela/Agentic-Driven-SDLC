"""execution_bounds.py — env-overridable execution thresholds (CH-15).
Hooks and agent prompts read these; no inline numeric literals anywhere else.
"""
from __future__ import annotations
import os


def _int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


MAX_TURNS_PER_SLICE = _int("SPINE_MAX_TURNS_PER_SLICE", 25)
N_PROGRESS_WINDOW = _int("SPINE_N_PROGRESS_WINDOW", 3)
SPEC_COMPLETION_HARD_CAP = _int("SPINE_SPEC_PASS_CAP", 7)
BLOCK_STREAK_HANDOFF = _int("SPINE_BLOCK_STREAK_HANDOFF", 5)
