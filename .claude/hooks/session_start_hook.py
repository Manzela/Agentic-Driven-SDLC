#!/usr/bin/env python3
"""SessionStart hook — state loader for the spec-to-evidence control plane.

Implements the Phase-0 deliverable of the design.md SessionStart row and
tasks.md task 7.1 (REQ-STATE-003 / REQ-STATE-005, Requirement 11.3):

  - Load git status, the progress file, and the coverage model (feature_list.json).
  - Count `unproven` vs `proven` in-scope coverage items.
  - Inject a structured-JSON summary into Claude Code context via stdout
    (named fields `git_status`, `unproven_count`, `proven_count`).

NON-BLOCKING BY CONTRACT (design.md hook-wiring "SessionStart" row): this hook
NEVER raises a block. It only computes/records; the PreToolUse integrity guard
(task 49.1) is the enforcement point that blocks on `resume_integrity_ok == false`.
Exit code is always 0.

`resume_integrity_ok` is the Phase-0 *shape* of the Phase-2 augmentation
(task 49.2): when a durable baseline hash is supplied, the hook recomputes the
resumed-state hash over `(git_status, progress)` and reports whether it matches.
The full Postgres-backed `run_state.resume_integrity_ok` WRITE via
`tools/state_integrity.py` is the Phase-2 wiring layered on top of this core.

PURE importable core (`session_start`, `compute_resume_hash`) + thin stdin shell
(`main`). The core has zero I/O — it takes plain values and returns a plain dict —
so the verifier can exercise it directly. `main` does the file/git I/O and is
wrapped so any failure logs a warning to stderr and still exits 0.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

# ── Module constants ────────────────────────────────────────────────────────

PROGRESS_FILE = "claude-progress.txt"
FEATURE_LIST_FILE = "feature_list.json"


# ── Resumed-state hash (Phase-0 shape of the Phase-2 state_integrity compute) ─

def compute_resume_hash(git_status: str | None, progress: str | None) -> str:
    """Deterministic sha256 over the resumed-state inputs `(git_status, progress)`.

    The two components are length-prefixed and joined so that no boundary
    ambiguity exists (e.g. ("a", "bc") cannot collide with ("ab", "c")).
    A missing component (None) is normalized to the empty string. The format is
    `sha256:<64-hex>`, matching the Evidence_Record `output_hash` convention.
    """
    gs = "" if git_status is None else str(git_status)
    pr = "" if progress is None else str(progress)
    payload = f"{len(gs)}:{gs}{len(pr)}:{pr}".encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


# ── Coverage counting ───────────────────────────────────────────────────────

def _count_statuses(feature_list: dict | None) -> tuple[int, int]:
    """Return (unproven_count, proven_count) over IN-SCOPE coverage items.

    Gates count ONLY `in_scope` items (design.md feature_list note; `in_scope`
    defaults to True when absent). A non-dict / malformed feature_list, or one
    with no `items`, yields (0, 0). Items with any other status (e.g. `failed`)
    are counted in neither bucket — the two named counts are the contract.
    """
    if not isinstance(feature_list, dict):
        return 0, 0
    items = feature_list.get("items")
    if not isinstance(items, list):
        return 0, 0
    unproven = 0
    proven = 0
    for item in items:
        if not isinstance(item, dict):
            continue
        if item.get("in_scope", True) is False:
            continue
        status = item.get("status")
        if status == "unproven":
            unproven += 1
        elif status == "proven":
            proven += 1
    return unproven, proven


# ── Pure importable core ────────────────────────────────────────────────────

def session_start(
    feature_list: dict | None,
    progress: str | None,
    git_status: str | None,
    durable_hash: str | None = None,
) -> dict:
    """Compute the SessionStart summary. PURE, NON-BLOCKING — never raises a block.

    Parameters
    ----------
    feature_list:
        The parsed `feature_list.json` document, or None when it is absent.
        When None, a stub summary with zero counts is returned.
    progress:
        Contents of `claude-progress.txt` (or None when absent).
    git_status:
        `git status --porcelain` output (or None when unavailable).
    durable_hash:
        The recorded baseline resumed-state hash to compare against. When
        provided, `resume_integrity_ok` is True iff the freshly computed hash of
        `(git_status, progress)` equals it; when None (a fresh, non-resumed
        session), `resume_integrity_ok` is True (a first run is never flagged).

    Returns
    -------
    dict with the required keys:
        summary (str), unproven_count (int), proven_count (int),
        resume_integrity_ok (bool).

    Also includes `git_status` (echoed, possibly empty string) so the structured
    stdout payload carries the named field the integration test asserts.
    """
    try:
        gs = "" if git_status is None else str(git_status)

        if feature_list is None:
            unproven_count = 0
            proven_count = 0
            summary = (
                "SessionStart: no feature_list.json present — fresh session. "
                "0 in-scope coverage items (0 unproven, 0 proven)."
            )
        else:
            unproven_count, proven_count = _count_statuses(feature_list)
            summary = (
                "SessionStart: loaded coverage model — "
                f"{unproven_count} unproven, {proven_count} proven in-scope item(s); "
                f"git status {'clean' if not gs.strip() else 'has changes'}."
            )

        if durable_hash is None:
            resume_integrity_ok = True
        else:
            resume_integrity_ok = (
                compute_resume_hash(git_status, progress) == durable_hash
            )

        return {
            "summary": summary,
            "unproven_count": unproven_count,
            "proven_count": proven_count,
            "resume_integrity_ok": resume_integrity_ok,
            "git_status": gs,
        }
    except Exception as exc:  # noqa: BLE001 — non-blocking by contract; degrade to a safe stub.
        return {
            "summary": f"SessionStart: degraded — {type(exc).__name__}: {exc}",
            "unproven_count": 0,
            "proven_count": 0,
            # Non-blocking: a degraded compute reports True so SessionStart itself
            # never induces a block; the PreToolUse integrity guard owns enforcement.
            "resume_integrity_ok": True,
            "git_status": "",
        }


# ── Thin stdin / file-I/O shell ─────────────────────────────────────────────

def _project_root() -> Path:
    """Repo root: two levels up from `.claude/hooks/` (…/.claude/hooks/<file>)."""
    return Path(__file__).resolve().parents[2]


def _read_git_status(root: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode != 0:
            return None
        return result.stdout
    except Exception:  # noqa: BLE001 — git absent / not a repo → no status.
        return None


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    except Exception:  # noqa: BLE001
        return None


def _read_feature_list(path: Path) -> dict | None:
    raw = _read_text(path)
    if raw is None:
        return None
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def main() -> int:
    """Claude-Code SessionStart entrypoint. Loads on-disk state, prints the
    structured-JSON summary to stdout, and ALWAYS exits 0 (non-blocking).

    A `durable_hash` may be supplied on the stdin event payload (key
    `durable_hash` / `resume_state_hash`) to exercise the resume-integrity
    comparison; absent it, the session is treated as fresh.
    """
    try:
        raw = sys.stdin.read()
    except Exception:  # noqa: BLE001 — no stdin available.
        raw = ""
    try:
        event = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        event = {}
    if not isinstance(event, dict):
        event = {}

    durable_hash = event.get("durable_hash") or event.get("resume_state_hash")

    try:
        root = _project_root()
        git_status = _read_git_status(root)
        progress = _read_text(root / PROGRESS_FILE)
        feature_list = _read_feature_list(root / FEATURE_LIST_FILE)
        result = session_start(
            feature_list=feature_list,
            progress=progress,
            git_status=git_status,
            durable_hash=durable_hash,
        )
        print(json.dumps(result))
    except Exception as exc:  # noqa: BLE001 — non-blocking by contract.
        print(f"session_start_hook: warning: {type(exc).__name__}: {exc}", file=sys.stderr)
    return 0  # ALWAYS non-blocking.


if __name__ == "__main__":
    sys.exit(main())
