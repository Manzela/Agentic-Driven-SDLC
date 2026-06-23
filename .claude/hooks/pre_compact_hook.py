#!/usr/bin/env python3
"""PreCompact hook — checkpoint durable state before compaction (REQ-STATE-002).

Fires when context compaction is imminent. Checkpoints the three durable-state
artifacts — ``claude-progress.txt``, the current evidence state, and
``feature_list.json`` — to the MAIN worktree so a post-compaction session can
reconstruct exactly where it was (REQ-STATE-002, contributing writer for
REQ-STATE-001's file+git persistence side; the Postgres half is Phase-2).

NON-BLOCKING by contract. A checkpoint is a pure write — it issues no allow/block
gate decision, so it is NOT an ``audit_log.append`` producer (only Stop /
PreToolUse / SubagentStop produce gate-audit entries). REQ-STATE-002 is verified
by unit + integration test (task 25.2), NOT by Z3 and by no Correctness
Property — a non-blocking checkpoint write has no SAT/UNSAT gating invariant.

Returns the checkpoint payload ``{"checkpointed": [<files>], "ok": True}``. Only
files that actually exist are listed; a missing artifact is skipped (and recorded
under ``"missing"``) rather than raising — the hook degrades, never blocks.

PURE importable core (`pre_compact`) + thin stdin shell (`main`).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.hook_telemetry import record_fire  # noqa: E402

# The durable-state artifacts this hook checkpoints, relative to the repo root.
# Globs are expanded against the resolved root; concrete paths are tried as-is.
_PROGRESS_FILE = "claude-progress.txt"
_FEATURE_LIST = "feature_list.json"
_EVIDENCE_GLOBS = ("evidence/**/*", "verification/evidence/**/*")
# Common alternate locations for the coverage model / progress file.
_FEATURE_CANDIDATES = (_FEATURE_LIST, ".kiro/feature_list.json", "state/feature_list.json")
_PROGRESS_CANDIDATES = (_PROGRESS_FILE, ".kiro/claude-progress.txt", "state/claude-progress.txt")


def _resolve_root(state: dict) -> Path:
    """Determine the repo root to checkpoint relative to."""
    root = (state or {}).get("repo_root") or (state or {}).get("cwd")
    if root:
        return Path(root)
    # Default: two levels up from .claude/hooks/ → the worktree root.
    return Path(__file__).resolve().parents[2]


def _first_existing(root: Path, candidates) -> Path | None:
    for rel in candidates:
        p = root / rel
        if p.is_file():
            return p
    return None


def _collect_targets(root: Path, state: dict) -> tuple[list[str], list[str]]:
    """Return (existing_relpaths, missing_labels) for the checkpoint set.

    ``state`` may override locations via ``progress_file`` / ``feature_list`` /
    ``evidence_paths`` (an explicit list of files); otherwise conventional
    locations are probed.
    """
    state = state or {}
    found: list[str] = []
    missing: list[str] = []

    def _rel(p: Path) -> str:
        try:
            return str(p.relative_to(root))
        except ValueError:
            return str(p)

    # 1) progress file
    override = state.get("progress_file")
    prog = Path(override) if override else None
    if prog is None or not prog.is_file():
        prog = _first_existing(root, _PROGRESS_CANDIDATES)
    if prog and prog.is_file():
        found.append(_rel(prog))
    else:
        missing.append(_PROGRESS_FILE)

    # 2) feature_list.json (the coverage model)
    override = state.get("feature_list")
    feat = Path(override) if override else None
    if feat is None or not feat.is_file():
        feat = _first_existing(root, _FEATURE_CANDIDATES)
    if feat and feat.is_file():
        found.append(_rel(feat))
    else:
        missing.append(_FEATURE_LIST)

    # 3) evidence state — explicit list, else conventional globs.
    explicit = state.get("evidence_paths")
    evidence_found = False
    if isinstance(explicit, (list, tuple)):
        for e in explicit:
            ep = Path(e)
            if not ep.is_absolute():
                ep = root / e
            if ep.is_file():
                found.append(_rel(ep))
                evidence_found = True
    else:
        for pattern in _EVIDENCE_GLOBS:
            for ep in sorted(root.glob(pattern)):
                if ep.is_file():
                    rp = _rel(ep)
                    if rp not in found:
                        found.append(rp)
                        evidence_found = True
    if not evidence_found:
        missing.append("evidence")

    return found, missing


def pre_compact(state: dict) -> dict:
    """Checkpoint progress + evidence + feature_list. NON-BLOCKING.

    Returns ``{"checkpointed": [<relpaths>], "ok": True, "missing": [...],
    "root": <root>}``. ``ok`` is ``True`` whenever the hook completed without an
    unhandled error — a missing artifact does not flip it to False, because this
    is a best-effort checkpoint, not a gate.
    """
    try:
        root = _resolve_root(state)
        checkpointed, missing = _collect_targets(root, state)
        return {
            "checkpointed": checkpointed,
            "ok": True,
            "missing": missing,
            "root": str(root),
        }
    except Exception as exc:  # noqa: BLE001 — non-blocking by contract.
        # Even on failure the payload is well-formed; ok stays True because a
        # checkpoint hook can never block compaction.
        return {
            "checkpointed": [],
            "ok": True,
            "missing": ["<error>"],
            "root": "",
            "error": f"pre_compact raised {type(exc).__name__}: {exc}",
        }


def main() -> int:
    """Thin stdin shell. Prints checkpoint JSON; ALWAYS exits 0 (non-blocking)."""
    raw = sys.stdin.read()
    try:
        state = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        state = {}
    record_fire("PreCompact", (state.get("session_id", "") if isinstance(state, dict) else ""))
    # Perform the checkpoint for its side effect / return value, but emit NO
    # stdout: PreCompact has no schema-valid stdout decision, so printing the
    # raw {"checkpointed":…} payload is INVALID INPUT. The pure core
    # (pre_compact) keeps returning the payload for the verifier; the shell just
    # runs it and exits 0 silently.
    pre_compact(state)
    # Exit 0 — PreCompact is a non-blocking checkpoint write; it cannot block
    # compaction. (Exit 2 is the blocking channel and is intentionally unused.)
    return 0


if __name__ == "__main__":
    sys.exit(main())
