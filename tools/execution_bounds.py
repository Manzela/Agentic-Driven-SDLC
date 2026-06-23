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


def _str(name: str, default: str) -> str:
    """Return a string config value from environment or default.

    Args:
        name: Environment variable name (e.g., 'ORPHAN_DETECTOR_BASELINE')
        default: Default string value if env var is not set

    Returns:
        Environment value if set; otherwise the provided default
    """
    return os.environ.get(name, default)


MAX_TURNS_PER_SLICE = _int("SPINE_MAX_TURNS_PER_SLICE", 25)
N_PROGRESS_WINDOW = _int("SPINE_N_PROGRESS_WINDOW", 3)
SPEC_COMPLETION_HARD_CAP = _int("SPINE_SPEC_PASS_CAP", 7)
BLOCK_STREAK_HANDOFF = _int("SPINE_BLOCK_STREAK_HANDOFF", 5)

# Diff-aware configuration (§3 of Phase-1 spec)
ORPHAN_DETECTOR_BASELINE = _str("ORPHAN_DETECTOR_BASELINE", "origin/main")
SEMGREP_BASELINE_STRATEGY = _str("SEMGREP_BASELINE_STRATEGY", "auto")
ORPHAN_ALLOWLIST_PATTERN = _str("ORPHAN_ALLOWLIST_PATTERN", "tools/.*")
SEMGREP_TIMEOUT_SECONDS = _int("SEMGREP_TIMEOUT_SECONDS", 120)
