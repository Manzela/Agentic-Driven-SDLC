"""depth_feed.py — the production feed for the local depth pillars (Task 14).

Without a feed, loop_gate.gated_advance receives empty changed_files and the fail-OPEN
depth pillars (Semgrep §4.2, orphans §3.3) no-op on every advance. This producer computes
the real diff so they actually RUN:

  baseline_commit  = git merge-base <baseline_ref> HEAD   (baseline_ref from execution_bounds)
  changed_files    = git diff --name-only <baseline_commit>
  feature_list_path = <root>/feature_list.json
  known_ids        = id-set of the committed feature_list model (the orphan dangling universe)

FAIL-SOFT: any git error (unreachable baseline, not a repo, fetch-depth:1) yields an empty
changed_files so the pillars simply skip — a feed failure must NEVER wedge the loop. It is a
NEUTRAL module (not in governed_pilot, which the_loop imports — that would be circular) so both
the_loop.gated_prove and the governed_pilot smoke-oracle can import it.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Dict

__all__ = ["compute_depth_feed"]


def _git(args: list, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=str(cwd),
                          capture_output=True, text=True, timeout=15)


def compute_depth_feed(root, *, baseline_ref: str | None = None) -> Dict[str, Any]:
    """Compute {baseline_commit, changed_files, feature_list_path, known_ids} for the
    depth pillars. baseline_ref defaults to execution_bounds.ORPHAN_DETECTOR_BASELINE
    (config-sourced, never hardcoded). Never raises."""
    if baseline_ref is None:
        try:
            from tools import execution_bounds as _eb
            baseline_ref = getattr(_eb, "ORPHAN_DETECTOR_BASELINE", "origin/main")
        except Exception:  # noqa: BLE001
            baseline_ref = "origin/main"

    root = Path(root)
    feed: Dict[str, Any] = {
        "baseline_commit": None,
        "changed_files": [],
        "feature_list_path": str(root / "feature_list.json"),
        "known_ids": set(),
    }

    # known_ids — the committed coverage model's id universe (the dangling-ref check needs it).
    try:
        model = json.loads((root / "feature_list.json").read_text(encoding="utf-8"))
        feed["known_ids"] = {
            i["id"] for i in model.get("items", []) if isinstance(i, dict) and "id" in i
        }
    except (FileNotFoundError, json.JSONDecodeError, OSError, UnicodeDecodeError):
        pass

    # baseline_commit + changed_files — fail-soft (an empty changed_files => pillars skip).
    try:
        mb = _git(["merge-base", baseline_ref, "HEAD"], root)
        if mb.returncode == 0 and mb.stdout.strip():
            feed["baseline_commit"] = mb.stdout.strip()
            diff = _git(["diff", "--name-only", feed["baseline_commit"]], root)
            if diff.returncode == 0:
                feed["changed_files"] = [f for f in diff.stdout.splitlines() if f.strip()]
    except Exception:  # noqa: BLE001 — "never raises" is the contract; a giant-diff
        pass            # MemoryError or any git oddity must fail-soft, not wedge the loop.

    return feed
