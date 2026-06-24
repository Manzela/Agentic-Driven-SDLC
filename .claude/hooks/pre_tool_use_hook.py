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
from tools.hook_telemetry import record_fire  # noqa: E402

COVERAGE_MODEL_PATHS = ("feature_list.json",)


def _is_coverage_path(p: str) -> bool:
    """True when ``p`` names the coverage model. Basename EQUALITY (normalized for a
    stray trailing space), NOT a loose ``endswith`` suffix — so `my_feature_list.json`
    / `docs/old_feature_list.json` do not false-match the model, and a trailing-space
    variant cannot dodge the gate (red-team N1/N2)."""
    base = os.path.basename((p or "").strip())
    return base in {os.path.basename(c) for c in COVERAGE_MODEL_PATHS}


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
            iid = el["id"]
            status = el.get("status")
            in_scope = el.get("in_scope")
            if iid in out:
                # Duplicate id (malformed). last-wins would let a proven shadow copy
                # hide behind an unproven one (red-team F7); surface the most
                # authority-sensitive status/scope instead so the gate still sees it.
                prev = out[iid]
                if prev.get("status") == "proven" or status == "proven":
                    status = "proven"
                if _is_excluded_scope(prev.get("in_scope")) and not _is_excluded_scope(in_scope):
                    in_scope = prev.get("in_scope")
            out[iid] = {"status": status, "in_scope": in_scope}
    return out


_STATUS_RE = re.compile(r'"status"\s*:\s*"([A-Za-z_]+)"')
_IN_SCOPE_RE = re.compile(r'"in_scope"\s*:\s*(true|false)')
_ID_RE = re.compile(r'"id"\s*:\s*"([^"]+)"')
_PROVEN_RE = re.compile(r'"status"\s*:\s*"proven"')
_IN_SCOPE_FALSE_RE = re.compile(r'"in_scope"\s*:\s*false')


def _is_excluded_scope(value) -> bool:
    """An item is out-of-scope (a human signature is required to birth/flip it there)
    when in_scope is PRESENT and not boolean True. Absent (None) defaults to in-scope.
    A non-bool literal ("false", 0, "no", even "true" as a string) is treated as
    excluded — malformed scope is conservatively gated, never silently in-scope (T11)."""
    return value is not None and value is not True


def _multiedit_value_flips(edits: list) -> set[str]:
    """Which of {'status','in_scope'} a fragment's old vs new actually FLIP IN VALUE.

    Extracts each field's VALUE token and reports a change only when that value moves,
    so 'status' merely APPEARING in an unrelated edit (a title change beside a status
    field) does not over-block a benign edit (red-team F6)."""
    changed: set[str] = set()
    for edit in edits or []:
        if not isinstance(edit, dict):
            continue
        old_str = edit.get("old_string", "") or ""
        new_str = edit.get("new_string", "") or ""
        for field, rx in (("status", _STATUS_RE), ("in_scope", _IN_SCOPE_RE)):
            om = rx.search(old_str)
            nm = rx.search(new_str)
            old_val = om.group(1) if om else None
            new_val = nm.group(1) if nm else None
            if (old_val is not None or new_val is not None) and old_val != new_val:
                changed.add(field)
    return changed


def _diff_coverage(before: dict, after: dict) -> tuple[dict, set[str], dict]:
    """Split a before/after item map into (insertions, mutations, deletions).

      insertions: {id: {status,in_scope}} for ids present ONLY in after (born items)
      mutations:  field names in {status,in_scope} whose value moved on a SHARED id
      deletions:  {id: {status,in_scope}} for ids present ONLY in before (removed)
    """
    insertions = {iid: av for iid, av in after.items() if iid not in before}
    deletions = {iid: bv for iid, bv in before.items() if iid not in after}
    mutations: set[str] = set()
    for iid, av in after.items():
        if iid in before:
            bv = before[iid]
            for f in ("status", "in_scope"):
                if av.get(f) is not None and av.get(f) != bv.get(f):
                    mutations.add(f)
    return insertions, mutations, deletions


def _fragment_signals(old_str: str, new_str: str) -> tuple[dict, set[str], dict]:
    """Conservative classifier for a fragment edit when the FULL document cannot be
    reconstructed (disk unreadable). Counts token deltas so the 'anchor already
    proven/false' evasion (red-team F3/F4) cannot hide a newly-introduced proven /
    in_scope:false, and an id-token removal is read as a deletion (F5)."""
    insertions: dict = {}
    mutations: set[str] = set()
    deletions: dict = {}
    old_ids = set(_ID_RE.findall(old_str))
    new_ids = set(_ID_RE.findall(new_str))
    removed = old_ids - new_ids
    added = new_ids - old_ids
    # An id present in old but not new = a deletion. We cannot read its fields, so
    # assume it is blockable (in-scope + unproven) — conservative for a non-verifier.
    for iid in removed:
        deletions[iid] = {"in_scope": True, "status": "unproven"}
    # A proven token introduced (count rises) = a move toward proven (flip or birth).
    if len(_PROVEN_RE.findall(new_str)) > len(_PROVEN_RE.findall(old_str)):
        mutations.add("status")
    # An in_scope:false token introduced = a move toward out-of-scope.
    if len(_IN_SCOPE_FALSE_RE.findall(new_str)) > len(_IN_SCOPE_FALSE_RE.findall(old_str)):
        mutations.add("in_scope")
    # Pure in-place edit (no id added/removed) — fall back to a value flip.
    if not removed and not added:
        mutations |= _multiedit_value_flips([{"old_string": old_str, "new_string": new_str}])
    return insertions, mutations, deletions


def _apply_edits(current: str, replacements: list) -> str:
    """Apply (old_string→new_string) replacements to ``current`` the way Edit/MultiEdit
    would (first occurrence each), to reconstruct the proposed full document."""
    out = current
    for old, new in replacements:
        out = out.replace(old, new, 1) if old else out + new
    return out


def _reconstruct(path: str, replacements: list):
    """Read the on-disk coverage model and apply ``replacements`` to get the TRUE
    before/after item maps. Returns None when the file cannot be read or is empty
    (no full document to diff against) — the caller then uses _fragment_signals."""
    try:
        current = Path(path).read_text(encoding="utf-8") if path else ""
    except OSError:
        return None
    if not current.strip():
        return None
    after = _apply_edits(current, replacements)
    return _coverage_items_by_id(current), _coverage_items_by_id(after)


def _changed_coverage_fields(tool_input: dict, *, path: str) -> tuple[dict, set[str], dict]:
    """Classify a proposed coverage-model write into (insertions, mutations, deletions).

    Robustness over fragments (red-team F3/F5/F6): a real Edit/MultiEdit on the large
    model uses SMALL fragments, which cannot reveal a whole-item insertion/deletion.
    So whenever the on-disk model is readable we RECONSTRUCT the true after-document
    (apply the replacement to the disk content) and diff the FULL before/after. Only
    when the fragments themselves are full coverage docs (the agent supplied the whole
    model) do we diff them directly; only when disk is unreadable do we fall back to
    conservative token signals.
    """
    old = tool_input.get("old_string")
    new = tool_input.get("new_string")
    content = tool_input.get("content")
    edits = tool_input.get("edits")

    if content is not None:  # Write — the proposed content IS the full after-document.
        try:
            current = Path(path).read_text(encoding="utf-8") if path else ""
        except OSError:
            current = ""
        return _diff_coverage(_coverage_items_by_id(current), _coverage_items_by_id(content))

    if old is not None or new is not None:  # Edit.
        before_decl = _coverage_items_by_id(old or "")
        after_decl = _coverage_items_by_id(new or "")
        if before_decl or after_decl:  # old/new are full coverage docs.
            return _diff_coverage(before_decl, after_decl)
        recon = _reconstruct(path, [(old or "", new or "")])  # fragment → reconstruct.
        if recon is not None:
            return _diff_coverage(*recon)
        return _fragment_signals(old or "", new or "")  # disk unreadable.

    if edits:  # MultiEdit.
        replacements = [(e.get("old_string", "") or "", e.get("new_string", "") or "")
                        for e in edits if isinstance(e, dict)]
        recon = _reconstruct(path, replacements)
        if recon is not None:
            return _diff_coverage(*recon)
        ins: dict = {}
        muts: set[str] = set()
        dels: dict = {}
        for o, n in replacements:  # disk unreadable → union per-edit signals.
            i2, m2, d2 = _fragment_signals(o, n)
            ins.update(i2)
            muts |= m2
            dels.update(d2)
        return ins, muts, dels

    return {}, set(), {}


def evaluate(*, tool_name: str, tool_input: dict, resolved_actor: str,
             human_signed: bool) -> dict:
    """Return {"decision": "allow"|"block", "reason": <steering string>}.

    The reason STEERS (located defect + one legitimate forward path + where to
    verify), keying on model shape (status/in_scope field, protected prefix,
    resolved actor), never on requirement text. Fails closed.
    """
    try:
        # Fail-CLOSED on a malformed payload: a PRESENT-but-non-dict tool_input is an
        # unverifiable write shape (the old `(tool_input or {}).get` raised here AND in
        # the except, exiting 1 = a NON-blocking error → fail OPEN). Deny it outright;
        # None (a genuinely input-less tool) coerces to {} and flows to the allow path.
        if tool_input is not None and not isinstance(tool_input, dict):
            return {"decision": "block", "reason":
                    "Malformed tool payload (tool_input is not an object); cannot verify "
                    f"write authority, treating as denied (fail-closed). HANDOFF to {MAIN_ACTOR} "
                    "if this is a harness issue; do not retry the same malformed call."}
        ti = tool_input if isinstance(tool_input, dict) else {}
        path = ti.get("file_path", "") or ""

        # Bash-write guard: a redirect / tee bypass is subject to the SAME authority
        # checks as a direct Edit/Write.
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
                # A coverage-model redirect/tee CANNOT be field-diffed, so it would
                # bypass R1/R2/R4 entirely (T9/T10/T11). Only the verifier (who owns
                # status + deletion) may write the model via shell; everyone else must
                # use Edit/Write so the gate can classify the change.
                if resolved_actor != VERIFIER_ROLE and _is_coverage_path(target):
                    return {"decision": "block", "reason":
                            f"The coverage model '{target}' may not be written via Bash "
                            "redirection or tee (you are "
                            f"'{resolved_actor}') — a shell write cannot be field-diffed, so "
                            "it would bypass the status/in_scope/deletion authority checks. "
                            "Use Edit or Write so the gate can classify the change, or hand "
                            "a status flip to the verifier."}
            return {"decision": "allow", "reason": "bash write permitted"}

        # Coverage-model field authority (detected by JSON delta). The classifier
        # splits the proposed write into new-id INSERTIONS, existing-id MUTATIONS,
        # and DELETIONS so birth, flip, and removal each route to the right owner.
        if _is_coverage_path(path):
            insertions, mutations, deletions = _changed_coverage_fields(ti, path=path)

            # R4 (T10) — a non-verifier may NOT delete an in-scope OR unproven item.
            # Deletion is the append-only bypass: removing an unmet item fakes COMPLETE.
            # Checked first so a rename (delete old + insert new) blocks on the deletion.
            if resolved_actor != VERIFIER_ROLE:
                blockable = [iid for iid, fv in deletions.items()
                             if fv.get("in_scope") is True or fv.get("status") == "unproven"]
                if blockable:
                    return {"decision": "block", "reason":
                            f"Cannot delete in-scope/unproven coverage item(s) {sorted(blockable)} "
                            f"(you are '{resolved_actor}'). The model is append-only for "
                            "non-verifiers — removing an unmet item fakes COMPLETE. If an item "
                            "is genuinely wrong, route a status:failed flip to the verifier; do "
                            "not delete it. The deletion is rejected at the gate."}

            # R1.2 (T9) / R2.2 (T11) — born-item rules. A new item may be born
            # status:unproven & in_scope:true (the insertion permit, R1.1/R2.1) — but
            # NOT born already-proven (only the verifier proves), nor born out-of-scope
            # without a human signature (in_scope is human-owned).
            for iid, fv in insertions.items():
                if fv.get("status") == "proven" and resolved_actor != VERIFIER_ROLE:
                    return {"decision": "block", "reason":
                            f"New item '{iid}' cannot be born status:proven (you are "
                            f"'{resolved_actor}'). Births are status:unproven; the verifier "
                            "flips it to proven only after the Evidence_Record is in place. "
                            "A born-proven item is a self-grade and is rejected at the gate."}
                if _is_excluded_scope(fv.get("in_scope")) and not human_signed:
                    return {"decision": "block", "reason":
                            f"New item '{iid}' cannot be born out-of-scope (in_scope="
                            f"{fv.get('in_scope')!r}) — in_scope is human-owned, and a "
                            "born-excluded item silently shrinks the completion set. Surface "
                            "the proposed in_scope change in your summary for a human to "
                            "sign; do not birth it excluded from the loop."}

            # R1 / R2 (unchanged) — existing-id field MUTATIONS.
            if "status" in mutations and resolved_actor != VERIFIER_ROLE:
                return {"decision": "block", "reason":
                        f"status is verifier-owned (you are '{resolved_actor}'). "
                        "To record a result, hand the item to the verifier subagent — "
                        "it runs the checks and writes the Evidence_Record that flips "
                        "the status. Do not edit status here; a self-graded flip is "
                        "rejected at SubagentStop."}
            if "in_scope" in mutations and not human_signed:
                return {"decision": "block", "reason":
                        "in_scope is human-owned — an agent cannot self-exempt an "
                        "item to reach COMPLETE. To change scope, surface the proposed "
                        "in_scope change in your summary for a human to sign; do not "
                        "flip it from inside the loop."}

            # Permitted: a benign coverage write (unproven births, benign field edits).
            return {"decision": "allow", "reason":
                    "coverage-model write permitted — births stay unproven & in-scope, "
                    "status verifier-owned, in_scope human-owned, deletions append-only."}

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
        # MUST NOT re-raise: a non-dict tool_input made the OLD `(tool_input or {}).get`
        # blow up here too, so the exception escaped and the process exited 1 (a
        # NON-blocking error → fail OPEN). Resolve the path defensively (F2).
        bad_path = tool_input.get("file_path", "<unknown>") if isinstance(tool_input, dict) else "<unknown>"
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
    # Valid-JSON-but-non-dict stdin (e.g. `[]`, `5`) parses fine but is a malformed event.
    # The `event.get(...)` below would raise AttributeError that escapes main() -> exit 1,
    # a NON-blocking code = FAIL OPEN on the one true prevention gate. Treat a non-dict
    # event as denied (fail-CLOSED), matching the docstring contract (whole-branch I10).
    if not isinstance(event, dict):
        print(
            "Malformed tool event (not an object); treating the write as denied "
            f"(fail-closed). HANDOFF to {MAIN_ACTOR} if this is a harness issue.",
            file=sys.stderr,
        )
        return 2
    record_fire("PreToolUse", event.get("session_id", ""),
                agent_type=event.get("agent_type", ""))
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
