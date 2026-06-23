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

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.hook_telemetry import record_fire  # noqa: E402

# ── Module constants ────────────────────────────────────────────────────────

PROGRESS_FILE = "claude-progress.txt"
FEATURE_LIST_FILE = "feature_list.json"
SETTINGS_FILE = ".claude/settings.json"

# The governance events whose registration the spine self-check asserts, paired
# with the expected hook-script basename for each. An event registered but
# pointing at a foreign script is a FALSE GREEN (A-HOOK-01): the slot exists yet
# an unrelated plugin owns it, so we match the registered command against the
# expected basename, not merely against the event's presence.
DEFAULT_EVENT_SCRIPTS = {
    "PreToolUse": "pre_tool_use_hook.py",
    "PostToolUse": "post_tool_use_hook.py",
    "Stop": "stop_hook.py",
    "SubagentStop": "subagent_stop_hook.py",
    "SessionStart": "session_start_hook.py",
    "PreCompact": "pre_compact_hook.py",
}

# The plugin whose Stop hook runs IN PARALLEL with this spine's Stop hook and
# shadows the governance HANDOFF/ALLOW gate unless explicitly disabled in
# settings.enabledPlugins. It is a shadow risk whenever it is NOT pinned to False.
SHADOWING_PLUGIN = "ralph-loop@claude-plugins-official"


# ── Spine self-check (D11) — loud on un-wiring / wrong-script / ralph shadow ──

def registered_commands(settings: dict | None) -> dict[str, list[str]]:
    """Return {event: [command-string, …]} for every event registered with at
    least one ``type:"command"`` hook in settings.json. Keys on the settings
    *shape* (hooks.<Event>[].hooks[].type/command), never on product content, so
    it generalizes to any roster. Capturing the command strings (not just the
    event name) lets the canary verify the slot points at THIS spine's hook
    rather than an unrelated plugin's (A-HOOK-01)."""
    out: dict[str, list[str]] = {}
    if not settings:
        return out
    hooks = settings.get("hooks")
    if not isinstance(hooks, dict):
        return out
    for event, groups in hooks.items():
        if not isinstance(groups, list):
            continue
        cmds: list[str] = []
        for group in groups:
            inner = (group or {}).get("hooks") if isinstance(group, dict) else None
            if not isinstance(inner, list):
                continue
            for h in inner:
                if isinstance(h, dict) and h.get("type") == "command":
                    cmds.append(str(h.get("command") or ""))
        if cmds:
            out[event] = cmds
    return out


def spine_status(
    settings: dict | None,
    required: list[str],
    event_scripts: dict[str, str],
    shadowing_plugin: str,
) -> dict:
    """Pure spine self-check over durable settings.json state. NON-BLOCKING.

    Asserts each ``required`` event is registered as a ``type:"command"`` hook
    AND that the registered command references the expected hook-script basename
    (so a foreign plugin silently owning a slot is caught, not read as GREEN).
    The shadowing plugin is a risk unless it is explicitly pinned to ``False`` in
    ``enabledPlugins`` (``enabledPlugins.get(plugin) is not False``).

    Returns ``{"ok", "missing", "wrong_script", "ralph_shadow_risk", "summary"}``.
    """
    cmds = registered_commands(settings)
    present = set(cmds.keys())

    missing = [e for e in required if e not in present]

    # An event registered but pointing at the wrong script is a FALSE GREEN.
    wrong_script: dict[str, str] = {}
    for ev in required:
        if ev in cmds and ev in event_scripts:
            expected = event_scripts[ev]
            if not any(expected in c for c in cmds[ev]):
                wrong_script[ev] = expected

    enabled = (settings or {}).get("enabledPlugins")
    enabled = enabled if isinstance(enabled, dict) else {}
    ralph_shadow_risk = enabled.get(shadowing_plugin) is not False

    ok = not missing and not wrong_script and not ralph_shadow_risk

    if ok:
        summary = (
            f"GOVERNANCE SPINE: PASS — {len(present & set(required))} required "
            f"event(s) registered to the expected scripts; {shadowing_plugin} "
            f"disabled."
        )
    else:
        parts = []
        if missing:
            parts.append(f"{len(missing)} event(s) not registered: {missing}")
        if wrong_script:
            parts.append(
                f"{len(wrong_script)} event(s) on the WRONG script: {wrong_script}"
            )
        if ralph_shadow_risk:
            parts.append(
                f"SHADOW RISK: {shadowing_plugin} not pinned False in enabledPlugins"
            )
        summary = "GOVERNANCE SPINE: FAIL — " + "; ".join(parts) + (
            f". Fix {SETTINGS_FILE} before relying on any gate."
        )

    return {
        "ok": ok,
        "missing": missing,
        "wrong_script": wrong_script,
        "ralph_shadow_risk": ralph_shadow_risk,
        "summary": summary,
    }


# ── Resumed-state hash (Phase-0 shape of the Phase-2 state_integrity compute) ─

def compute_resume_hash(git_status: str | None, progress: str | None) -> str:
    """DEPRECATED — superseded by tools.state_integrity.compute_state_hash.

    This Phase-0 hash framed only (git_status, progress) — it omitted feature_list and
    used a different (length-prefixed, sha256:-tagged) encoding than the producer
    (pre_compact) writes, so the two could NEVER match and Property 26 was neutered
    (red-team). session_start() now verifies via state_integrity.check_resume_integrity;
    this function is retained only for its standalone determinism test.

    Deterministic sha256 over `(git_status, progress)`, length-prefixed so no boundary
    ambiguity exists (("a","bc") cannot collide with ("ab","c")); None → "". Format
    `sha256:<64-hex>`.
    """
    gs = "" if git_status is None else str(git_status)
    pr = "" if progress is None else str(progress)
    payload = f"{len(gs)}:{gs}{len(pr)}:{pr}".encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _read_run_state_hash(root: Path) -> str | None:
    """Read run_state.resume_state_hash from run_state.json (the pre_compact -> SessionStart
    delivery channel), or None when absent/unreadable. Never raises."""
    p = Path(root) / "run_state.json"
    if not p.is_file():
        return None
    try:
        row = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        return None
    if isinstance(row, dict):
        h = row.get("resume_state_hash")
        return h if h else None
    return None


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
            # Verify via the SAME canonical hash the pre_compact producer writes
            # (state_integrity over git_status + progress + feature_list) so producer
            # and consumer agree. The old local compute_resume_hash framed a different,
            # feature_list-less payload and could never match (red-team F1/F2/F4).
            from tools.state_integrity import check_resume_integrity
            resume_integrity_ok = check_resume_integrity(
                durable_hash, git_status or "", progress or "", feature_list or {})

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


def _read_settings(path: Path) -> dict | None:
    """Best-effort read of settings.json. None on absence or parse error — both
    are spine-self-check signals (absent/malformed → no hooks registered)."""
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
    record_fire("SessionStart", event.get("session_id", ""))

    try:
        root = _project_root()
        # Delivery channel: the pre_compact producer persists resume_state_hash into
        # run_state.json. Read it as the baseline when the event did not carry one, so
        # the resume-integrity loop closes WITHOUT depending on the harness threading
        # the hash onto the SessionStart event (red-team F3).
        if not durable_hash:
            durable_hash = _read_run_state_hash(root)
        git_status = _read_git_status(root)
        progress = _read_text(root / PROGRESS_FILE)
        feature_list = _read_feature_list(root / FEATURE_LIST_FILE)
        result = session_start(
            feature_list=feature_list,
            progress=progress,
            git_status=git_status,
            durable_hash=durable_hash,
        )

        # ── Spine self-check (D11): loud on un-wiring / wrong-script / ralph
        #    shadow. NON-BLOCKING — fold the self-check summary into the
        #    context the A5 self-check surfaces to the operator.
        try:
            settings = _read_settings(root / SETTINGS_FILE)
            status = spine_status(
                settings,
                list(DEFAULT_EVENT_SCRIPTS.keys()),
                DEFAULT_EVENT_SCRIPTS,
                SHADOWING_PLUGIN,
            )
            result["spine_ok"] = status["ok"]
            result["spine_summary"] = status["summary"]
            result["summary"] = result["summary"] + " " + status["summary"]
        except Exception as exc:  # noqa: BLE001 — non-blocking; never vanish silently.
            result["spine_summary"] = (
                f"GOVERNANCE SPINE: self-check did not complete "
                f"({type(exc).__name__}: {exc})."
            )
            result["summary"] = result["summary"] + " " + result["spine_summary"]

        # Claude Code hook-output schema: SessionStart injects context ONLY via
        # {"hookSpecificOutput":{"hookEventName":"SessionStart",
        #   "additionalContext":…}}. Emitting the raw result dict (bare
        # top-level "summary"/"unproven_count"/… keys) is INVALID INPUT — the
        # A5 self-check summary must ride additionalContext, never a bare field.
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": result["summary"],
        }}))
    except Exception as exc:  # noqa: BLE001 — non-blocking by contract.
        print(f"session_start_hook: warning: {type(exc).__name__}: {exc}", file=sys.stderr)
    return 0  # ALWAYS non-blocking.


if __name__ == "__main__":
    sys.exit(main())
