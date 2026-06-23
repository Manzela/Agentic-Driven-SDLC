#!/usr/bin/env python3
"""PostToolUse hook — in-loop lint + SAST + wiring feedback (REQ-VERIFY-004).

Fires after a ``Write`` / ``Edit`` / ``MultiEdit`` completes. Runs lint, an
edit-time SAST pass (Semgrep ONLY — CodeQL is the CI gate per REQ-SEC-001, NOT
run here), and a static wiring check over the changed files, then SURFACES every
finding as NEXT-TURN feedback for the model.

NEVER BLOCKS. By the time PostToolUse fires the write has already landed, so a
block would be a no-op it cannot undo — the design pins this as the
"PostToolUse never-blocks (exit-1) invariant" (design.md:845). Accordingly:

  * the pure core returns ``{"decision": "non_block", "feedback": [...]}``;
  * the stdin shell exits ``1`` (non-blocking feedback channel — exit 2 would be
    the blocking channel, which this hook MUST NEVER use);
  * it issues no allow/block gate decision and therefore is deliberately EXCLUDED
    from the ``audit_log.append`` producer set (only Stop / PreToolUse /
    SubagentStop produce gate-audit entries — design.md:131, :229);
  * it does NOT enforce the 0-HIGH/CRITICAL SAST threshold (Req 20.1) — that is
    the CI SAST gate (REQ-SEC-001). Here HIGH/CRITICAL findings are feedback.

``runners`` is an injectable dict of callables so the verifier can drive the
pure core with deterministic fakes; when ``None`` the real (best-effort,
exception-swallowing) runners are used. A failing or missing runner degrades to
a single advisory feedback line — it never raises, never blocks.

Enforces: REQ-VERIFY-004, REQ-STEER-002, REQ-EXEC-010, and Req 8.1 (PostToolUse
is the TRIGGER that invokes the wiring checker on changed files, task 18.1).
PURE importable core (`post_tool_use`) + thin stdin shell (`main`).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Tool calls whose completion carries changed file paths worth checking.
_EDIT_TOOLS = ("Write", "Edit", "MultiEdit")

# Severities surfaced verbatim; none of them block (feedback only).
_SEVERITIES = ("error", "warning", "info", "high", "critical", "medium", "low")


def _changed_paths(tool_input: dict, tool_name: str) -> list[str]:
    """Extract the file paths a write/edit tool touched, best-effort."""
    if tool_name not in _EDIT_TOOLS:
        return []
    ti = tool_input or {}
    paths: list[str] = []
    fp = ti.get("file_path") or ti.get("path")
    if isinstance(fp, str) and fp:
        paths.append(fp)
    # MultiEdit-style payloads: a list of edits each carrying its own path.
    for edit in ti.get("edits", []) or []:
        if isinstance(edit, dict):
            efp = edit.get("file_path") or edit.get("path")
            if isinstance(efp, str) and efp and efp not in paths:
                paths.append(efp)
    for p in ti.get("file_paths", []) or []:
        if isinstance(p, str) and p and p not in paths:
            paths.append(p)
    return paths


def _normalize_findings(source: str, raw) -> list[dict]:
    """Coerce a runner's return value into a list of feedback records.

    Accepts a list of dicts, a list of strings, or anything else (stringified).
    Never raises — a malformed runner result becomes one advisory line.
    """
    out: list[dict] = []
    if raw is None:
        return out
    if isinstance(raw, dict):
        raw = [raw]
    if isinstance(raw, (list, tuple)):
        for item in raw:
            if isinstance(item, dict):
                sev = str(item.get("severity", "warning")).lower()
                if sev not in _SEVERITIES:
                    sev = "warning"
                out.append({
                    "source": source,
                    "severity": sev,
                    "path": item.get("path") or item.get("file") or "",
                    "line": item.get("line"),
                    "rule": item.get("rule") or item.get("check_id") or "",
                    "message": str(item.get("message", item)),
                })
            else:
                out.append({"source": source, "severity": "warning",
                            "path": "", "line": None, "rule": "",
                            "message": str(item)})
    else:
        out.append({"source": source, "severity": "warning", "path": "",
                    "line": None, "rule": "", "message": str(raw)})
    return out


def _safe_run(runners: dict, name: str, paths: list[str]) -> list[dict]:
    """Invoke one runner over the changed paths, swallowing all errors."""
    fn = (runners or {}).get(name)
    if fn is None:
        return []
    try:
        return _normalize_findings(name, fn(paths))
    except Exception as exc:  # noqa: BLE001 — a runner failure is feedback, never a block.
        return [{
            "source": name, "severity": "info", "path": "", "line": None,
            "rule": "runner-error",
            "message": f"{name} runner raised {type(exc).__name__}: {exc} "
                       f"(degraded to advisory; not blocking)",
        }]


def post_tool_use(event: dict, runners: dict = None) -> dict:
    """Collect lint/SAST/wiring findings as next-turn feedback. NEVER blocks.

    Returns ``{"decision": "non_block", "feedback": [<record>, ...]}``. Each
    record is ``{source, severity, path, line, rule, message}``. The feedback
    list is advisory only — the contract guarantees the decision is always
    ``"non_block"`` regardless of finding severity.
    """
    try:
        event = event or {}
        tool_name = event.get("tool_name") or event.get("tool") or ""
        tool_input = event.get("tool_input") or {}
        paths = _changed_paths(tool_input, tool_name)

        if runners is None:
            runners = _default_runners()

        feedback: list[dict] = []
        if paths:
            # Order is the design's edit-time sequence: lint, then SAST
            # (Semgrep only), then the static wiring check (Req 8.1 trigger).
            for runner_name in ("lint", "sast", "wiring"):
                feedback.extend(_safe_run(runners, runner_name, paths))
        # No changed paths → no findings, but still a well-formed non_block.
        return {"decision": "non_block", "feedback": feedback}
    except Exception as exc:  # noqa: BLE001 — invariant: this hook can NEVER block.
        return {"decision": "non_block", "feedback": [{
            "source": "post_tool_use", "severity": "info", "path": "",
            "line": None, "rule": "hook-error",
            "message": f"post_tool_use raised {type(exc).__name__}: {exc} "
                       f"(non-blocking by invariant)",
        }]}


# --------------------------------------------------------------------------- #
# Real runners (best-effort, exception-swallowing). Absent tooling degrades to
# an empty finding list rather than an error — the hook stays advisory-only.
# --------------------------------------------------------------------------- #

def _real_lint(paths: list[str]) -> list[dict]:
    return _run_subprocess(["ruff", "check", "--output-format", "json", *paths],
                           source="lint", json_array=True)


def _real_sast(paths: list[str]) -> list[dict]:
    # Semgrep ONLY at edit time (CodeQL is the CI gate, REQ-SEC-001).
    return _run_subprocess(["semgrep", "--quiet", "--json", *paths],
                           source="sast", json_key="results")


def _real_wiring(paths: list[str]) -> list[dict]:
    # Req 8.1: PostToolUse is the trigger; the wiring engine lives in tools/.
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
        from tools.wiring_checker import check_wiring  # type: ignore
    except Exception:
        return []  # Wiring engine is a Phase-1 component; absent → no findings.
    try:
        return _normalize_findings("wiring", check_wiring(paths))
    except Exception:
        return []


def _run_subprocess(cmd, *, source, json_array=False, json_key=None) -> list[dict]:
    import shutil
    import subprocess
    if shutil.which(cmd[0]) is None:
        return []  # Tool not installed → silently no findings (advisory only).
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except Exception:
        return []
    out = (proc.stdout or "").strip()
    if not out:
        return []
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return [{"severity": "info", "message": out[:500]}]
    if json_key is not None and isinstance(data, dict):
        data = data.get(json_key, [])
    if json_array and not isinstance(data, list):
        data = [data]
    return _normalize_findings(source, data)


def _default_runners() -> dict:
    return {"lint": _real_lint, "sast": _real_sast, "wiring": _real_wiring}


def main() -> int:
    """Thin stdin shell. Prints feedback JSON; ALWAYS exits 1 (non-blocking)."""
    raw = sys.stdin.read()
    try:
        event = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        event = {}
    result = post_tool_use(event)
    print(json.dumps(result))
    # Exit 1 = non-blocking feedback channel. NEVER 2 (which would block) and
    # NEVER 0-with-block — the PostToolUse never-blocks invariant (design.md:845).
    return 1


if __name__ == "__main__":
    sys.exit(main())
