#!/usr/bin/env python3
"""PreToolUse gate — field-level write authority (actor-independence fix #4).

The only true prevention gate (exit 2 blocks before a write lands). Enforces:

  * the coverage model's ``status`` field is writable ONLY by the verifier role
    (a runtime-resolved actor of ``verifier``);
  * the coverage model's ``in_scope`` field is mutable ONLY by a human-signed
    change (an autonomous agent cannot self-exempt an item to fake COMPLETE);
  * protected artifacts (tests, schema, CI, hooks, settings) may not be edited
    by a non-root actor (only the root ``main`` session / a human) — and the
    same authority check applies to a ``Bash`` redirect / ``tee`` bypass.

Field authority is detected by DIFFING THE JSON, not by a phantom
``tool_input["field"]`` key (a real Edit payload carries
``file_path``/``old_string``/``new_string``; a real Write carries
``file_path``/``content`` — neither carries ``field``, so the old predicate was
inert on every real edit). ``_changed_coverage_fields`` parses the proposed
mutation — for Edit it diffs ``old_string``/``new_string``; for Write it diffs
the on-disk coverage model against the proposed ``content`` per item id — and
reports which of ``status``/``in_scope`` actually change value.

Identity is resolved by tools/actor_identity (fix #1), never from the payload.
Likewise ``human_signed`` (the in_scope authority signal) is resolved by
``_resolve_human_signed`` from an out-of-band runtime signal (the ``HUMAN_SIGNED``
env var / a session-keyed signature artifact), NEVER from ``tool_input`` — an
agent cannot self-exempt an item by setting ``tool_input["human_signed"]=true``.

On a BLOCK the steering reason is written to STDERR and the hook exits 2 (Claude
Code ignores stdout JSON on exit 2, so the reason must be on stderr or it is
lost). PURE importable core (``evaluate``) + thin stdin shell (``main``). Fails
closed.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.spine_roles import (  # noqa: E402  (single-source role + path constants)
    MAIN_ACTOR,
    PROTECTED_PREFIXES,
    VERIFIER_ROLE,
)

COVERAGE_MODEL_PATHS = ("feature_list.json",)


def _resolve_human_signed(event: dict) -> bool:
    """Resolve human-sign authority from an OUT-OF-BAND signal (fix #1).

    The writing agent must never declare its own authority inside the tool
    payload, so ``tool_input["human_signed"]`` is deliberately IGNORED. The
    signal is resolved instead from runtime state the agent cannot write:
    the ``HUMAN_SIGNED`` env var (set by the human-approval step), or a
    human-signature artifact keyed on the runtime ``session_id``. Until that
    out-of-band signal exists, return ``False`` (R2 always denies). Fail closed.
    """
    if os.environ.get("HUMAN_SIGNED", "").strip().lower() in {"1", "true", "yes"}:
        return True
    session_id = event.get("session_id")
    if session_id:
        sig = (
            Path(__file__).resolve().parents[2]
            / ".claude" / "approvals" / f"{session_id}.human-signed"
        )
        if sig.exists():
            return True
    return False


def _bash_write_targets(command: str) -> list[str]:
    """Extract filesystem write targets from a Bash command string.

    Parses ``>``, ``>>`` redirections and ``tee`` / ``tee -a`` arguments so a
    write that routes around Edit/Write via shell redirection is still subject
    to the same authority check. Best-effort: an unparseable command yields the
    targets found by the regex fallback (never raises).
    """
    if not command:
        return []
    targets: list[str] = []

    # Redirection: `> path` / `>> path` (also `1> path`, `2>> path`).
    for m in re.finditer(r"\d*>>?\s*([^\s;|&<>]+)", command):
        tgt = m.group(1).strip("\"'")
        if tgt:
            targets.append(tgt)

    # tee / tee -a <file...>: tokenize, then take non-flag args after a `tee`.
    try:
        tokens = shlex.split(command)
    except ValueError:
        tokens = command.split()
    i = 0
    while i < len(tokens):
        if tokens[i] == "tee":
            j = i + 1
            while j < len(tokens):
                tok = tokens[j]
                if tok in {"|", ";", "&&", "||", ">", ">>"}:
                    break
                if not tok.startswith("-"):
                    targets.append(tok.strip("\"'"))
                j += 1
            i = j
        else:
            i += 1
    return targets


def _coverage_items_by_id(content: str) -> dict:
    """Parse a coverage-model document into {item_id: {status, in_scope}}.

    Best-effort: a non-JSON or non-coverage-shaped string yields ``{}``.
    """
    try:
        data = json.loads(content)
    except (json.JSONDecodeError, TypeError):
        return {}
    items = data.get("items") if isinstance(data, dict) else None
    if not isinstance(items, list):
        return {}
    out = {}
    for el in items:
        if isinstance(el, dict) and "id" in el:
            out[el["id"]] = {
                "status": el.get("status"),
                "in_scope": el.get("in_scope"),
            }
    return out


def _changed_coverage_fields(tool_input: dict, *, path: str) -> set[str]:
    """Return which of {'status','in_scope'} a real Edit/Write would CHANGE.

      * **Edit** — diff the per-item field map parsed from ``old_string`` vs
        ``new_string``. If neither fragment parses as a coverage doc, fall back
        to a value-moving textual signal (field name present in ``new_string``
        and the literal pre/post values differ).
      * **Write** — diff the on-disk coverage model (current ``content`` of
        ``path``) against the proposed ``content``, per item id.

    Empty set ⇒ no status/in_scope value actually moves ⇒ the gate does not
    fire (a benign coverage write is allowed). SubagentStop's hash
    re-derivation is the authoritative backstop for any flip this early gate
    cannot see.
    """
    changed: set[str] = set()
    old = tool_input.get("old_string")
    new = tool_input.get("new_string")
    content = tool_input.get("content")

    if old is not None or new is not None:  # Edit shape.
        before = _coverage_items_by_id(old or "")
        after = _coverage_items_by_id(new or "")
        if before or after:
            for iid, av in after.items():
                bv = before.get(iid, {})
                for f in ("status", "in_scope"):
                    if av.get(f) is not None and av.get(f) != bv.get(f):
                        changed.add(f)
        else:
            for f in ("status", "in_scope"):
                if f in (new or "") and (old or "") != (new or ""):
                    changed.add(f)
        return changed

    if content is not None:  # Write shape.
        try:
            current = Path(path).read_text(encoding="utf-8") if path else ""
        except OSError:
            current = ""
        before = _coverage_items_by_id(current)
        after = _coverage_items_by_id(content)
        for iid, av in after.items():
            bv = before.get(iid, {})
            for f in ("status", "in_scope"):
                if av.get(f) is not None and av.get(f) != bv.get(f):
                    changed.add(f)
        return changed

    return changed


def evaluate(*, tool_name: str, tool_input: dict, resolved_actor: str,
             human_signed: bool) -> dict:
    """Return {"decision": "allow"|"block", "reason": <steering string>}.

    The reason STEERS (located defect + one legitimate forward path + where to
    verify), keying on model shape (status/in_scope field, protected prefix,
    resolved actor), never on requirement text. Fails closed.
    """
    try:
        ti = tool_input or {}
        path = ti.get("file_path", "") or ""

        # Bash-write guard: a redirect / tee bypass is subject to the SAME
        # protected-artifact authority check as a direct Edit/Write.
        if tool_name == "Bash":
            for target in _bash_write_targets(ti.get("command", "") or ""):
                if resolved_actor != MAIN_ACTOR and any(
                    target.startswith(p) for p in PROTECTED_PREFIXES
                ):
                    return {"decision": "block", "reason":
                            f"Protected path '{target}' may not be written via Bash "
                            "redirection, tee, or another tool — the same authority "
                            "check applies. Hand the change to the main session or a "
                            "human; do not route around the guard."}
            return {"decision": "allow", "reason": "bash write permitted"}

        # Coverage-model field authority (detected by JSON delta).
        if any(path.endswith(p) for p in COVERAGE_MODEL_PATHS):
            changed = _changed_coverage_fields(ti, path=path)
            # R1 — status is verifier-owned. Steer to the verifier subagent.
            if "status" in changed and resolved_actor != VERIFIER_ROLE:
                return {"decision": "block", "reason":
                        f"status is verifier-owned (you are '{resolved_actor}'). "
                        "To record a result, hand the item to the verifier subagent — "
                        "it runs the checks and writes the Evidence_Record that flips "
                        "the status. Do not edit status here; a self-graded flip is "
                        "rejected at SubagentStop."}
            # R2 — in_scope is human-owned. Steer to a human-signed change.
            if "in_scope" in changed and not human_signed:
                return {"decision": "block", "reason":
                        "in_scope is human-owned — an agent cannot self-exempt an "
                        "item to reach COMPLETE. To change scope, surface the proposed "
                        "in_scope change in your summary for a human to sign; do not "
                        "flip it from inside the loop."}
            # R4 — coverage-model write permitted, with the standing guard named.
            return {"decision": "allow", "reason":
                    "coverage-model write permitted — status stays verifier-owned, "
                    "in_scope human-owned."}

        # R3 — Protected-artifact guard. Non-root actors may not edit
        # tests/schema/CI/hooks/settings. Name the out AND forbid the bypass.
        if resolved_actor != MAIN_ACTOR and any(
            path.startswith(p) for p in PROTECTED_PREFIXES
        ):
            return {"decision": "block", "reason":
                    f"{path} is {MAIN_ACTOR}/human-owned (tests, schema, CI, hooks). "
                    "To change behavior, edit the implementation under your slice and "
                    "let the verifier re-run; if the artifact itself is wrong, HANDOFF "
                    f"to {MAIN_ACTOR} with a one-line rationale. Do NOT write it via "
                    "Bash redirection, tee, or another tool — the same authority check "
                    "applies."}

        return {"decision": "allow", "reason": "write permitted"}
    except Exception as exc:  # noqa: BLE001 — fail closed, but steer the agent.
        bad_path = (tool_input or {}).get("file_path", "<unknown>")
        return {"decision": "block", "reason":
                f"Could not verify write authority for {bad_path}; treating as denied "
                "(fail-closed). Re-issue the edit with the file you actually intend to "
                f"change, or HANDOFF to {MAIN_ACTOR} if you believe this file is yours "
                f"to edit. [{type(exc).__name__}]"}


def main() -> int:
    raw = sys.stdin.read()
    try:
        event = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        print(
            "Could not parse the tool event; treating the write as denied "
            f"(fail-closed). Retry the edit; if it keeps failing, HANDOFF to {MAIN_ACTOR}.",
            file=sys.stderr,
        )
        return 2
    from tools.actor_identity import resolve_identity
    try:
        actor = resolve_identity(event).actor_agent
    except ValueError as exc:
        print(
            "Could not resolve who is making this write (no runtime session_id); "
            "treating as denied (fail-closed). This is a harness/wiring issue — "
            f"HANDOFF to {MAIN_ACTOR}, do not retry. [{exc}]",
            file=sys.stderr,
        )
        return 2
    ti = event.get("tool_input", {})
    decision = evaluate(
        tool_name=event.get("tool_name", "") or "",
        tool_input=ti,
        resolved_actor=actor,
        # human_signed is resolved out-of-band (fix #1) — NEVER from tool_input.
        human_signed=_resolve_human_signed(event),
    )
    if decision["decision"] == "allow":
        # Claude Code hook-output schema: PreToolUse has NO valid top-level
        # "decision". An allow is exit 0 with NO stdout (a bare
        # {"decision":"allow"} is INVALID INPUT and spams "Invalid input" on
        # every tool call). The implicit-allow path is the conformant one.
        return 0
    # Block: the reason is read only on stderr (stdout JSON is ignored on exit 2).
    print(decision["reason"], file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
